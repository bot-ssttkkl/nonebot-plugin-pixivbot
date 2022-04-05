import asyncio
from collections import OrderedDict
import functools
import math
import random
import time
import typing
from io import BytesIO

from nonebot import logger
from nonebot.adapters.onebot.v11 import Bot
from nonebot.adapters.onebot.v11 import Message, MessageSegment
from nonebot.adapters.onebot.v11.event import MessageEvent

from ..config import Config
from ..data_source import PixivBindings, PixivDataSource
from ..model import Illust, LazyIllust
from ..errors import QueryError
from .pkg_context import context


class NoReplyError(Exception):
    def __init__(self, reason=""):
        self.reason = reason

    def __str__(self):
        return self.reason


def fill_id(func):
    @functools.wraps(func)
    def wrapped(self, *args, bot: Bot,
                event: MessageEvent = None,
                user_id: typing.Optional[int] = None,
                group_id: typing.Optional[int] = None,
                **kwargs):
        if event is not None:
            if group_id is None and "group_id" in event.__fields__ and event.group_id:
                group_id = event.group_id
            if user_id is None and "user_id" in event.__fields__ and event.user_id:
                user_id = event.user_id
        return func(self, *args, bot=bot, event=event, user_id=user_id, group_id=group_id, **kwargs)

    return wrapped


def retry(func):
    @functools.wraps(func)
    async def wrapped(self, *args, bot: Bot,
                      event: MessageEvent = None,
                      user_id: typing.Optional[int] = None,
                      group_id: typing.Optional[int] = None,
                      silently: bool = False,
                      **kwargs):
        err = None
        for t in range(5):
            try:
                await func(self, *args, bot=bot, event=event, user_id=user_id, group_id=group_id, silently=silently, **kwargs)
                return
            except NoReplyError:
                return
            except QueryError as e:
                if e.reason and not silently:
                    await self._send(bot, "获取失败："+e.reason, event=event, user_id=user_id, group_id=group_id)
                return
            except asyncio.TimeoutError as e:
                err = e
                logger.warning("Timeout")
            except Exception as e:
                err = e
                logger.exception(e)

        if not silently:
            if isinstance(err, asyncio.TimeoutError):
                await self._send(bot, "获取超时", event=event, user_id=user_id, group_id=group_id)
            else:
                await self._send(bot, f"发生内部错误：{type(e)}{e}", event=event, user_id=user_id, group_id=group_id)

    return wrapped


@context.export_singleton()
class Distributor:
    TYPES = ["ranking", "illust", "self.random_illust", "random_user_illust", "random_recommended_illust",
             "random_bookmark"]

    conf = context.require(Config)
    data_source = context.require(PixivDataSource)
    pixiv_bindings = context.require(PixivBindings)

    def __init__(self, session_expires_in: int = 10*60):
        self.session_expires_in = session_expires_in
        self._distribute_func = {
            "ranking": self.distribute_ranking,
            "illust": self.distribute_illust,
            "random_illust": self.distribute_random_illust,
            "random_user_illust": self.distribute_random_user_illust,
            "random_recommended_illust": self.distribute_random_recommended_illust,
            "random_bookmark": self.distribute_random_bookmark,
        }
        self._prev_req_func = OrderedDict()
        self._prev_resp_illust_id = OrderedDict()

    def _pop_expired_req(self):
        now = time.time()
        while len(self._prev_req_func) > 0:
            (user_id, group_id), (timestamp, _) = next(
                iter(self._prev_req_func.items()))
            if now - timestamp > self.session_expires_in:
                self._prev_req_func.popitem(last=False)
                logger.info(f"popped expired req: ({user_id}, {group_id})")
            else:
                break

    def _push_req(self, func: typing.Callable, *,
                  user_id: typing.Optional[int] = None,
                  group_id: typing.Optional[int] = None):
        self._pop_expired_req()
        if (user_id, group_id) in self._prev_req_func:
            self._prev_req_func.move_to_end((user_id, group_id))
        self._prev_req_func[(user_id, group_id)] = time.time(), func

    def _get_req(self,  *,
                 user_id: typing.Optional[int] = None,
                 group_id: typing.Optional[int] = None) -> typing.Callable:
        self._pop_expired_req()
        if (user_id, group_id) in self._prev_req_func:
            (_, func) = self._prev_req_func[(user_id, group_id)]
            self._prev_req_func[(user_id, group_id)] = time.time(), func
            self._prev_req_func.move_to_end((user_id, group_id))
            return func
        elif user_id is not None and group_id is not None:  # 获取上一条群订阅的请求
            return self._get_req(group_id=group_id)
        else:
            return None

    def _pop_expired_resp(self):
        now = time.time()
        while len(self._prev_resp_illust_id) > 0:
            (user_id, group_id), (timestamp, _) = next(
                iter(self._prev_resp_illust_id.items()))
            if now - timestamp > self.session_expires_in:
                self._prev_resp_illust_id.popitem(last=False)
                logger.info(f"popped expired resp: ({user_id}, {group_id})")
            else:
                break

    def _push_resp(self, illust_id: int, *,
                   user_id: typing.Optional[int] = None,
                   group_id: typing.Optional[int] = None) -> int:
        self._pop_expired_resp()
        if (user_id, group_id) in self._prev_resp_illust_id:
            self._prev_resp_illust_id.move_to_end((user_id, group_id))
        self._prev_resp_illust_id[(user_id, group_id)] = time.time(), illust_id

    def _get_resp(self,  *,
                  user_id: typing.Optional[int] = None,
                  group_id: typing.Optional[int] = None) -> int:
        self._pop_expired_resp()
        if (user_id, group_id) in self._prev_resp_illust_id:
            (_, illust_id) = self._prev_resp_illust_id[(user_id, group_id)]
            return illust_id
        elif user_id is not None and group_id is not None:  # 获取上一条群订阅的响应
            return self._get_resp(group_id=group_id)
        else:
            return 0

    async def _make_illust_msg(self, illust: typing.Union[LazyIllust, Illust],
                               number: typing.Optional[int] = None) -> Message:
        if isinstance(illust, LazyIllust):
            illust = await illust.get()

        msg = Message()

        if illust.has_tags(self.conf.pixiv_block_tags):
            if self.conf.pixiv_block_action == "no_image":
                msg.append("该画像因含有不可描述的tag而被自主规制\n")
                if number is not None:
                    msg.append(f"#{number}")
                msg.append(f"「{illust.title}」\n"
                           f"作者：{illust.user.name}\n"
                           f"https://www.pixiv.net/artworks/{illust.id}")
            elif self.conf.pixiv_block_action == "completely_block":
                msg.append("该画像因含有不可描述的tag而被自主规制\n")
            elif self.conf.pixiv_block_action == "no_reply":
                raise NoReplyError()
        else:
            with BytesIO() as bio:
                bio.write(await self.data_source.download(illust))

                msg.append(MessageSegment.image(bio))
                if number is not None:
                    msg.append(f"#{number}")
                msg.append(f"「{illust.title}」\n"
                           f"作者：{illust.user.name}\n"
                           f"https://www.pixiv.net/artworks/{illust.id}")
            return msg

    async def _make_illusts_msg(self, illusts: typing.List[typing.Union[LazyIllust, Illust]],
                                num_start: int = 1) -> Message:
        tasks = []
        for i, illust in enumerate(illusts):
            tasks.append(asyncio.create_task(
                self._make_illust_msg(illust, i + num_start)))

        await asyncio.wait(tasks, return_when=asyncio.ALL_COMPLETED)

        msg = Message()
        for t in tasks:
            msg.extend(await t)
        return msg

    @staticmethod
    async def _random_illust(illusts: typing.List[LazyIllust], random_method: str) -> LazyIllust:
        if random_method == "uniform":
            # 概率相等
            probability = [1 / len(illusts)] * len(illusts)
        else:
            illusts = filter(lambda x: x.loaded, illusts)  # 只在已加载的插画中选择
            illusts = list(illusts)
            if random_method == "bookmark_proportion":
                # 概率正比于书签数
                sum_bm = 0
                for x in illusts:
                    sum_bm += x.total_bookmarks + 10  # 加10平滑

                probability = [0] * len(illusts)
                for i, x in enumerate(illusts):
                    probability[i] = (x.total_bookmarks + 10) / sum_bm
            elif random_method == "view_proportion":
                # 概率正比于查看人数
                sum_view = 0
                for x in illusts:
                    sum_view += x.total_view + 10  # 加10平滑

                probability = [0] * len(illusts)
                for i, x in enumerate(illusts):
                    probability[i] = (x.total_view + 10) / sum_view
            elif random_method == "timedelta_proportion":
                # 概率正比于 exp((当前时间戳 - 画像发布时间戳) / 3e7)
                now = time.time()
                delta_time = [now - x.create_date.timestamp() for x in illusts]
                probability = [math.exp(-x * 3e-7) for x in delta_time]
                sum_poss = sum(probability)
                for i in range(len(probability)):
                    probability[i] = probability[i] / sum_poss
            else:
                raise ValueError(
                    f"illegal random_method value: {random_method}")

        for i in range(1, len(probability)):
            probability[i] = probability[i] + probability[i - 1]

        ran = random.random()

        # 二分查找
        first, last = 0, len(probability) - 1
        while first < last:
            mid = (first + last) // 2
            if probability[mid] > ran:
                last = mid
            else:
                first = mid + 1
        return illusts[first]

    @staticmethod
    async def _send(bot: Bot, msg: typing.Union[str, Message], *,
                    event: MessageEvent = None,
                    user_id: typing.Optional[int] = None,
                    group_id: typing.Optional[int] = None):
        if event is not None:
            if isinstance(event, MessageEvent):
                if isinstance(msg, Message):
                    msg = Message(
                        [MessageSegment.reply(event.message_id), *msg])
                else:
                    msg = Message([MessageSegment.reply(
                        event.message_id), MessageSegment.text(msg)])
            await bot.send(event, msg)
        else:
            await bot.send_msg(user_id=user_id, group_id=group_id, message=msg)

    async def _send_illust(self, bot: Bot, illust: typing.Union[Illust, LazyIllust], *,
                           event: MessageEvent = None,
                           user_id: typing.Optional[int] = None,
                           group_id: typing.Optional[int] = None):
        self._push_resp(illust.id, user_id=user_id, group_id=group_id)

        msg = await self._make_illust_msg(illust)
        await self._send(bot, msg, event=event, user_id=user_id, group_id=group_id)

    async def _choice_and_send_illust(self, bot: Bot, illusts: typing.List[typing.Union[Illust, LazyIllust]],
                                      random_method: str, *,
                                      event: MessageEvent = None,
                                      user_id: typing.Optional[int] = None,
                                      group_id: typing.Optional[int] = None):
        if len(illusts) > 0:
            illust = await self._random_illust(illusts, random_method)
            logger.info(f"select {illust.id}")

            await self._send_illust(bot, illust, event=event, user_id=user_id, group_id=group_id)
        else:
            raise QueryError("别看了，没有的。")

    async def distribute(self, type: str,
                         *, bot: Bot,
                         event: MessageEvent = None,
                         user_id: typing.Optional[int] = None,
                         group_id: typing.Optional[int] = None,
                         silently: bool = False, **kwargs):
        await self._distribute_func[type](bot=bot, event=event, user_id=user_id, group_id=group_id,
                                          silently=silently, **kwargs)

    @fill_id
    @retry
    async def distribute_ranking(self, mode: typing.Optional[str] = None,
                                 range: typing.Optional[typing.Union[typing.Sequence[int], int]] = None,
                                 *, bot: Bot,
                                 event: MessageEvent = None,
                                 user_id: typing.Optional[int] = None,
                                 group_id: typing.Optional[int] = None,
                                 silently: bool = False):
        self._push_req(functools.partial(self.distribute_ranking, mode, range),
                       user_id=user_id, group_id=group_id)

        if mode is None:
            mode = self.conf.pixiv_ranking_default_mode

        if range is None:
            range = self.conf.pixiv_ranking_default_range

        if isinstance(range, int):
            num = range
            if num > self.conf.pixiv_ranking_fetch_item:
                raise QueryError(
                    f'仅支持查询{self.conf.pixiv_ranking_fetch_item}名以内的插画')
            else:
                illusts = await self.data_source.illust_ranking(mode, self.conf.pixiv_ranking_fetch_item,
                                                                block_tags=self.conf.pixiv_block_tags)
                await self._send_illust(bot, illusts[num - 1], event=event, user_id=user_id, group_id=group_id)
        else:
            start, end = range
            if end - start + 1 > self.conf.pixiv_ranking_max_item_per_query:
                raise QueryError(
                    f"仅支持一次查询{self.conf.pixiv_ranking_max_item_per_query}张以下插画")
            elif start > end:
                raise QueryError("范围不合法")
            elif end > self.conf.pixiv_ranking_fetch_item:
                raise QueryError(
                    f'仅支持查询{self.conf.pixiv_ranking_fetch_item}名以内的插画')
            else:
                illusts = await self.data_source.illust_ranking(mode)

                while start <= end:
                    msg = await self._make_illusts_msg(
                        illusts[start:min(end + 1, start + self.conf.pixiv_ranking_max_item_per_msg)], start)
                    await self._send(bot, msg, event=event, user_id=user_id, group_id=group_id)
                    start += self.conf.pixiv_ranking_max_item_per_msg

    @fill_id
    @retry
    async def distribute_illust(self, illust: typing.Union[int, Illust],
                                *, bot: Bot,
                                event: MessageEvent = None,
                                user_id: typing.Optional[int] = None,
                                group_id: typing.Optional[int] = None,
                                silently: bool = False):
        self._push_req(functools.partial(self.distribute_illust, illust),
                       user_id=user_id, group_id=group_id)

        if isinstance(illust, int):
            illust = await self.data_source.illust_detail(illust)
        await self._send_illust(bot, illust, event=event, user_id=user_id, group_id=group_id)

    @fill_id
    @retry
    async def distribute_random_illust(self, word: str,
                                       *, bot: Bot,
                                       event: MessageEvent = None,
                                       user_id: typing.Optional[int] = None,
                                       group_id: typing.Optional[int] = None,
                                       silently: bool = False):
        self._push_req(functools.partial(self.distribute_random_illust, word),
                       user_id=user_id, group_id=group_id)

        illusts = await self.data_source.search_illust(word,
                                                       self.conf.pixiv_random_illust_max_item,
                                                       self.conf.pixiv_random_illust_max_page,
                                                       self.conf.pixiv_block_tags,
                                                       self.conf.pixiv_random_illust_min_bookmark,
                                                       self.conf.pixiv_random_illust_min_view)

        await self._choice_and_send_illust(bot, illusts, self.conf.pixiv_random_illust_method,
                                           event=event, user_id=user_id, group_id=group_id)

    @fill_id
    @retry
    async def distribute_random_user_illust(self, user: typing.Union[str, int],
                                            *, bot: Bot,
                                            event: MessageEvent = None,
                                            user_id: typing.Optional[int] = None,
                                            group_id: typing.Optional[int] = None,
                                            silently: bool = False):
        self._push_req(functools.partial(self.distribute_random_user_illust, user),
                       user_id=user_id, group_id=group_id)

        if isinstance(user, str):
            users = await self.data_source.search_user(user)
            if len(users) == 0:
                raise QueryError("未找到用户")
            else:
                user = users[0].id
        illusts = await self.data_source.user_illusts(user,
                                                      self.conf.pixiv_random_user_illust_max_item,
                                                      self.conf.pixiv_random_user_illust_max_page,
                                                      self.conf.pixiv_block_tags,
                                                      self.conf.pixiv_random_user_illust_min_bookmark,
                                                      self.conf.pixiv_random_user_illust_min_view)

        await self._choice_and_send_illust(bot, illusts, self.conf.pixiv_random_user_illust_method,
                                           event=event, user_id=user_id, group_id=group_id)

    @fill_id
    @retry
    async def distribute_random_recommended_illust(self, *, bot: Bot,
                                                   event: MessageEvent = None,
                                                   user_id: typing.Optional[int] = None,
                                                   group_id: typing.Optional[int] = None,
                                                   silently: bool = False):
        self._push_req(self.distribute_random_recommended_illust,
                       user_id=user_id, group_id=group_id)

        illusts = await self.data_source.recommended_illusts(self.conf.pixiv_random_recommended_illust_max_item,
                                                             self.conf.pixiv_random_recommended_illust_max_page,
                                                             self.conf.pixiv_block_tags,
                                                             self.conf.pixiv_random_recommended_illust_min_bookmark,
                                                             self.conf.pixiv_random_recommended_illust_min_view)

        await self._choice_and_send_illust(bot, illusts, self.conf.pixiv_random_recommended_illust_method,
                                           event=event, user_id=user_id, group_id=group_id)

    @fill_id
    @retry
    async def distribute_random_bookmark(self, pixiv_user_id: int = 0, *, bot: Bot,
                                         event: MessageEvent = None,
                                         user_id: typing.Optional[int] = None,
                                         group_id: typing.Optional[int] = None,
                                         silently: bool = False):
        self._push_req(functools.partial(self.distribute_random_bookmark, pixiv_user_id),
                       user_id=user_id, group_id=group_id)

        if not pixiv_user_id:
            pixiv_user_id = await self.pixiv_bindings.get_binding(user_id)

        if not pixiv_user_id:
            pixiv_user_id = self.conf.pixiv_random_bookmark_user_id

        if not pixiv_user_id:
            raise QueryError("未绑定Pixiv账号")

        illusts = await self.data_source.user_bookmarks(pixiv_user_id,
                                                        self.conf.pixiv_random_bookmark_max_item,
                                                        self.conf.pixiv_random_bookmark_max_page,
                                                        self.conf.pixiv_block_tags,
                                                        self.conf.pixiv_random_bookmark_min_bookmark,
                                                        self.conf.pixiv_random_bookmark_min_view)

        await self._choice_and_send_illust(bot, illusts, self.conf.pixiv_random_bookmark_method,
                                           event=event, user_id=user_id, group_id=group_id)

    @fill_id
    @retry
    async def distribute_related_illust(self, illust_id: int = 0, *, bot: Bot,
                                        event: MessageEvent = None,
                                        user_id: typing.Optional[int] = None,
                                        group_id: typing.Optional[int] = None,
                                        silently: bool = False):
        self._push_req(functools.partial(self.distribute_related_illust, illust_id),
                       user_id=user_id, group_id=group_id)

        if illust_id == 0:
            illust_id = self._get_resp(user_id=user_id, group_id=group_id)
            if illust_id == 0:
                raise QueryError("你还没有发送过请求")
            logger.info(f"prev resp illust_id: {illust_id}")

        illusts = await self.data_source.related_illusts(illust_id,
                                                         self.conf.pixiv_random_related_illust_max_item,
                                                         self.conf.pixiv_random_related_illust_max_page,
                                                         self.conf.pixiv_block_tags,
                                                         self.conf.pixiv_random_related_illust_min_bookmark,
                                                         self.conf.pixiv_random_related_illust_min_view)

        await self._choice_and_send_illust(bot, illusts, self.conf.pixiv_random_related_illust_method,
                                           event=event, user_id=user_id, group_id=group_id)

    @fill_id
    async def redistribute(self, *, bot: Bot,
                           event: MessageEvent = None,
                           user_id: typing.Optional[int] = None,
                           group_id: typing.Optional[int] = None):
        resp = self._get_req(user_id=user_id, group_id=group_id)

        if resp is None:
            await self._send(bot, "你还没有发送过请求", event=event, user_id=user_id, group_id=group_id)
        else:
            await resp(bot=bot, event=event, user_id=user_id, group_id=group_id)


__all__ = ("Distributor",)
