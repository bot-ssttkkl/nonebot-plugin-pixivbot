import asyncio
import math
import random
import time
import typing
import functools
from io import BytesIO

from nonebot import logger
from nonebot.adapters.cqhttp import Bot
from nonebot.adapters.cqhttp import Message, MessageSegment
from nonebot.adapters.cqhttp.event import Event, MessageEvent

from .config import Config, conf
from .data_source import PixivDataSource, data_source
from .model.Illust import Illust
from .utils.errors import NoRetryError
from .utils.errors import QueryError


def _Distributor__auto_retry(func):
    @functools.wraps(func)
    async def wrapped(self, *args, bot: Bot,
                      event: MessageEvent = None,
                      user_id: typing.Optional[int] = None,
                      group_id: typing.Optional[int] = None,
                      silently: bool = False, **kwargs):
        err = None
        for t in range(5):
            try:
                await func(self, *args, bot=bot, event=event, user_id=user_id, group_id=group_id, **kwargs)
                return
            except NoRetryError as e:
                if e.reason and not silently:
                    await self._send(bot, e.reason, event=event, user_id=user_id, group_id=group_id)
                return
            except QueryError as e:
                if e.reason and not silently:
                    await self._send(bot, "获取失败：" + e.reason, event=event, user_id=user_id, group_id=group_id)
                return
            except asyncio.TimeoutError as e:
                err = e
                logger.warning(e)
            except Exception as e:
                err = e
                logger.exception(e)

        if err is not None and not silently:
            if isinstance(err, asyncio.TimeoutError):
                await self._send(bot, "获取超时", event=event, user_id=user_id, group_id=group_id)
            else:
                await self._send(bot, "发生内部错误：" + str(err), event=event, user_id=user_id, group_id=group_id)

    return wrapped


class Distributor:
    TYPES = ["ranking", "illust", "self.random_illust", "random_user_illust", "random_recommended_illust",
             "random_bookmark"]

    def __init__(self, conf: Config, data_source: PixivDataSource):
        self.conf = conf
        self.data_source = data_source
        self._distribute_func = {
            "ranking": self.distribute_ranking,
            "illust": self.distribute_illust,
            "random_illust": self.distribute_random_illust,
            "random_user_illust": self.distribute_random_user_illust,
            "random_recommended_illust": self.distribute_random_recommended_illust,
            "random_bookmark": self.distribute_random_bookmark,
        }

    async def make_illust_msg(self, illust: Illust, number: typing.Optional[int] = None) -> Message:
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
                raise NoRetryError()
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

    async def make_illusts_msg(self, illusts: typing.List[Illust], num_start: int = 1) -> Message:
        msg = Message()
        for i, illust in enumerate(illusts):
            msg.extend(await self.make_illust_msg(illust, i + num_start))
        return msg

    @staticmethod
    def random_illust(illusts: typing.List[Illust], random_method: str) -> Illust:
        if random_method == "bookmark_proportion":
            # 概率正比于书签数
            sum_bm = 0
            for x in illusts:
                sum_bm += x.total_bookmarks + 10  # 加10平滑
            probability = [(x.total_bookmarks + 10) / sum_bm for x in illusts]
        elif random_method == "view_proportion":
            # 概率正比于查看人数
            sum_view = 0
            for x in illusts:
                sum_view += x.total_view + 10  # 加10平滑
            probability = [(x.total_view + 10) / sum_view for x in illusts]
        elif random_method == "timedelta_proportion":
            # 概率正比于 exp((当前时间戳 - 画像发布时间戳) / 3e7)
            now = time.time()
            delta_time = [now - x.create_date.timestamp() for x in illusts]
            probability = [math.exp(-x * 3e-7) for x in delta_time]
            sum_poss = sum(probability)
            for i in range(len(probability)):
                probability[i] = probability[i] / sum_poss
        elif random_method == "uniform":
            # 概率相等
            probability = [1 / len(illusts)] * len(illusts)
        else:
            raise ValueError(f"illegal random_method value: {random_method}")

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

    async def _send(self, bot: Bot, msg: typing.Union[str, Message], *,
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

    async def distribute(self, type: str,
                         *, bot: Bot,
                         event: MessageEvent = None,
                         user_id: typing.Optional[int] = None,
                         group_id: typing.Optional[int] = None,
                         silently: bool = False, **kwargs):
        await self._distribute_func[type](bot=bot, event=event, user_id=user_id, group_id=group_id,
                                          silently=silently, **kwargs)

    @__auto_retry
    async def distribute_ranking(self, mode: typing.Optional[str] = None,
                                 range: typing.Optional[typing.Union[typing.Sequence[int], int]] = None,
                                 *, bot: Bot,
                                 event: MessageEvent = None,
                                 user_id: typing.Optional[int] = None,
                                 group_id: typing.Optional[int] = None,
                                 silently: bool = False):
        if mode is None:
            mode = self.conf.pixiv_ranking_default_mode

        if range is None:
            range = self.conf.pixiv_ranking_default_range

        if isinstance(range, int):
            num = range
            if num > self.conf.pixiv_ranking_fetch_item:
                raise NoRetryError(
                    f'仅支持查询{self.conf.pixiv_ranking_fetch_item}名以内的插画')
            else:
                illusts = await self.data_source.illust_ranking(mode, self.conf.pixiv_ranking_fetch_item,
                                                                block_tags=self.conf.pixiv_block_tags)
                msg = await self.make_illust_msg(illusts[num - 1])
                await self._send(bot, msg, event=event, user_id=user_id, group_id=group_id)
        else:
            start, end = range
            if end - start + 1 > self.conf.pixiv_ranking_max_item_per_query:
                raise NoRetryError(
                    f"仅支持一次查询{self.conf.pixiv_ranking_max_item_per_query}张以下插画")
            elif start > end:
                raise NoRetryError("范围不合法")
            elif end > self.conf.pixiv_ranking_fetch_item:
                raise NoRetryError(
                    f'仅支持查询{self.conf.pixiv_ranking_fetch_item}名以内的插画')
            else:
                illusts = await self.data_source.illust_ranking(mode)

                while start <= end:
                    msg = await self.make_illusts_msg(illusts[start:min(end+1, start+self.conf.pixiv_ranking_max_item_per_msg)], start)
                    await self._send(bot, msg, event=event, user_id=user_id, group_id=group_id)
                    start += self.conf.pixiv_ranking_max_item_per_msg

    @__auto_retry
    async def distribute_illust(self, illust: typing.Union[int, Illust],
                                *, bot: Bot,
                                event: MessageEvent = None,
                                user_id: typing.Optional[int] = None,
                                group_id: typing.Optional[int] = None,
                                silently: bool = False):
        if isinstance(illust, int):
            illust = await self.data_source.illust_detail(illust)
        msg = await self.make_illust_msg(illust)
        await self._send(bot, msg, event=event, user_id=user_id, group_id=group_id)

    @__auto_retry
    async def distribute_random_illust(self, word: str,
                                       *, bot: Bot,
                                       event: MessageEvent = None,
                                       user_id: typing.Optional[int] = None,
                                       group_id: typing.Optional[int] = None,
                                       silently: bool = False):
        illusts = await self.data_source.search_illust(word,
                                                       self.conf.pixiv_random_illust_max_item,
                                                       self.conf.pixiv_random_illust_max_page,
                                                       self.conf.pixiv_block_tags,
                                                       self.conf.pixiv_random_illust_min_bookmark,
                                                       self.conf.pixiv_random_illust_min_view)

        if len(illusts) > 0:
            illust = self.random_illust(
                illusts, self.conf.pixiv_random_illust_method)
            logger.debug(
                f"{len(illusts)} illusts found, select {illust.title} ({illust.id}).")
            msg = await self.make_illust_msg(illust)
            await self._send(bot, msg, event=event, user_id=user_id, group_id=group_id)
        else:
            raise NoRetryError("别看了，没有的。")

    @__auto_retry
    async def distribute_random_user_illust(self, user: typing.Union[str, int],
                                            *, bot: Bot,
                                            event: MessageEvent = None,
                                            user_id: typing.Optional[int] = None,
                                            group_id: typing.Optional[int] = None,
                                            silently: bool = False):
        if isinstance(user, str):
            users = await self.data_source.search_user(user)
            if len(users) == 0:
                raise NoRetryError("未找到用户")
            else:
                user = users[0].id
        illusts = await self.data_source.user_illusts(user,
                                                      self.conf.pixiv_random_user_illust_max_item,
                                                      self.conf.pixiv_random_user_illust_max_page,
                                                      self.conf.pixiv_block_tags,
                                                      self.conf.pixiv_random_user_illust_min_bookmark,
                                                      self.conf.pixiv_random_user_illust_min_view)

        if len(illusts) > 0:
            illust = self.random_illust(
                illusts, self.conf.pixiv_random_illust_method)
            logger.debug(
                f"{len(illusts)} illusts found, select {illust.title} ({illust.id}).")
            msg = await self.make_illust_msg(illust)
            await self._send(bot, msg, event=event, user_id=user_id, group_id=group_id)
        else:
            raise NoRetryError("别看了，没有的。")

    @__auto_retry
    async def distribute_random_recommended_illust(self, *, bot: Bot,
                                                   event: MessageEvent = None,
                                                   user_id: typing.Optional[int] = None,
                                                   group_id: typing.Optional[int] = None,
                                                   silently: bool = False):
        illusts = await self.data_source.recommended_illusts(self.conf.pixiv_random_recommended_illust_max_item,
                                                             self.conf.pixiv_random_recommended_illust_max_page,
                                                             self.conf.pixiv_block_tags,
                                                             self.conf.pixiv_random_recommended_illust_min_bookmark,
                                                             self.conf.pixiv_random_recommended_illust_min_view)

        if len(illusts) > 0:
            illust = self.random_illust(
                illusts, self.conf.pixiv_random_recommended_illust_method)
            logger.debug(
                f"{len(illusts)} illusts found, select {illust.title} ({illust.id}).")
            msg = await self.make_illust_msg(illust)
            await self._send(bot, msg, event=event, user_id=user_id, group_id=group_id)
        else:
            raise NoRetryError("别看了，没有的。")

    @__auto_retry
    async def distribute_random_bookmark(self, *, bot: Bot,
                                         event: MessageEvent = None,
                                         user_id: typing.Optional[int] = None,
                                         group_id: typing.Optional[int] = None,
                                         silently: bool = False):
        illusts = await self.data_source.user_bookmarks(self.conf.pixiv_random_bookmark_user_id,
                                                        self.conf.pixiv_random_bookmark_max_item,
                                                        self.conf.pixiv_random_bookmark_max_page,
                                                        self.conf.pixiv_block_tags,
                                                        self.conf.pixiv_random_bookmark_min_bookmark,
                                                        self.conf.pixiv_random_bookmark_min_view)

        if len(illusts) > 0:
            illust = self.random_illust(
                illusts, self.conf.pixiv_random_bookmark_method)
            logger.debug(
                f"{len(illusts)} illusts found, select {illust.title} ({illust.id}).")
            msg = await self.make_illust_msg(illust)
            await self._send(bot, msg, event=event, user_id=user_id, group_id=group_id)
        else:
            raise NoRetryError("别看了，没有的。")


distributor = Distributor(conf, data_source)

__all__ = ("Distributor", "distributor")
