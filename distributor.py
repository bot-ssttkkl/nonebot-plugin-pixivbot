import typing
from io import BytesIO

from nonebot import logger
from nonebot.adapters.cqhttp import Bot
from nonebot.adapters.cqhttp import Message, MessageSegment

from .config import Config, conf
from .data_source import PixivDataSource, data_source
from .utils.errors import NoReplyError
from .utils.errors import QueryError
from .model.Illust import Illust
from .utils import random_illust


class Distributor:
    TYPES = ["ranking", "illust", "random_illust", "random_user_illust", "random_recommended_illust", "random_bookmark"]

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

    async def make_illust_msg(self, illust: Illust) -> Message:
        msg = Message()

        if illust.has_tags(self.conf.pixiv_block_tags):
            if self.conf.pixiv_block_action == "no_image":
                msg.append("该画像因含有不可描述的tag而被自主规制\n")
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
                msg.append(f"「{illust.title}」\n"
                           f"作者：{illust.user.name}\n"
                           f"https://www.pixiv.net/artworks/{illust.id}")
            return msg

    async def make_illusts_msg(self, illusts: typing.List[Illust], num_start=1) -> Message:
        msg = Message()
        for i, illust in enumerate(illusts):
            if illust.has_tags(self.conf.pixiv_block_tags):
                if self.conf.pixiv_block_action == "no_image":
                    msg.append("该画像因含有不可描述的tag而被自主规制\n")
                    msg.append(f"#{i + num_start}「{illust.title}」\n"
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
                    msg.append(f"#{i + num_start}「{illust.title}」\n"
                               f"作者：{illust.user.name}\n"
                               f"https://www.pixiv.net/artworks/{illust.id}")
        return msg

    async def distribute(self, type: str, bot: Bot,
                         member_id: typing.Optional[int] = None,
                         group_id: typing.Optional[int] = None,
                         no_error_msg: bool = False, *args, **kwargs):
        self._distribute_func[type](bot=bot, member_id=member_id, group_id=group_id,
                                    no_error_msg=no_error_msg, *args, **kwargs)

    async def distribute_ranking(self, mode: typing.Optional[str],
                                 range: typing.Optional[typing.Union[typing.Sequence[int], int]],
                                 bot: Bot,
                                 member_id: typing.Optional[int] = None,
                                 group_id: typing.Optional[int] = None,
                                 no_error_msg: bool = False):
        try:
            if mode is None:
                mode = self.conf.pixiv_ranking_default_mode

            if range is None:
                range = self.conf.pixiv_ranking_default_range

            if isinstance(range, int):
                num = range
                if num > self.conf.pixiv_ranking_fetch_item:
                    await bot.send_msg(user_id=member_id, group_id=group_id,
                                       message=f'仅支持查询{self.conf.pixiv_ranking_fetch_item}名以内的插画')
                else:
                    illusts = await self.data_source.illust_ranking(mode, self.conf.pixiv_ranking_fetch_item,
                                                                    block_tags=self.conf.pixiv_block_tags)
                    msg = await self.make_illust_msg(illusts[num - 1])
                    await bot.send_msg(user_id=member_id, group_id=group_id, message=msg)
            else:
                start, end = range
                if end - start + 1 > self.conf.pixiv_ranking_max_item_per_msg:
                    await bot.send_msg(user_id=member_id, group_id=group_id,
                                       message=f"仅支持一次查询{self.conf.pixiv_ranking_max_item_per_msg}张以下插画")
                elif start > end:
                    await bot.send_msg(user_id=member_id, group_id=group_id,
                                       message="范围不合法")
                elif end > self.conf.pixiv_ranking_fetch_item:
                    await bot.send_msg(user_id=member_id, group_id=group_id,
                                       message=f'仅支持查询{self.conf.pixiv_ranking_fetch_item}名以内的插画')
                else:
                    illusts = await self.data_source.illust_ranking(mode)
                    msg = await self.make_illusts_msg(illusts[start - 1:end], start)
                    await bot.send_msg(user_id=member_id, group_id=group_id, message=msg)
        except NoReplyError:
            pass
        except QueryError as e:
            if not no_error_msg:
                await bot.send_msg(user_id=member_id, group_id=group_id, message=e.reason)
            logger.warning(e)
        except TimeoutError as e:
            if not no_error_msg:
                await bot.send_msg(user_id=member_id, group_id=group_id, message="下载超时")
            logger.warning(e)
        except Exception as e:
            logger.exception(e)

    async def distribute_illust(self, illust: typing.Union[int, Illust],
                                bot: Bot,
                                member_id: typing.Optional[int] = None,
                                group_id: typing.Optional[int] = None,
                                no_error_msg: bool = False):
        try:
            if isinstance(illust, int):
                illust = await self.data_source.illust_detail(illust)
            msg = await self.make_illust_msg(illust)
            await bot.send_msg(user_id=member_id, group_id=group_id, message=msg)
        except NoReplyError:
            pass
        except QueryError as e:
            if not no_error_msg:
                await bot.send_msg(user_id=member_id, group_id=group_id, message=e.reason)
            logger.warning(e)
        except TimeoutError as e:
            if not no_error_msg:
                await bot.send_msg(user_id=member_id, group_id=group_id, message="下载超时")
            logger.warning(e)
        except Exception as e:
            logger.exception(e)

    async def distribute_random_illust(self, word: str,
                                       bot: Bot,
                                       member_id: typing.Optional[int] = None,
                                       group_id: typing.Optional[int] = None,
                                       no_error_msg: bool = False):
        try:
            illusts = await self.data_source.search_illust(word,
                                                           self.conf.pixiv_random_illust_max_item,
                                                           self.conf.pixiv_random_illust_max_page,
                                                           self.conf.pixiv_block_tags,
                                                           self.conf.pixiv_random_illust_min_bookmark,
                                                           self.conf.pixiv_random_illust_min_view)

            if len(illusts) > 0:
                illust = random_illust(illusts, self.conf.pixiv_random_illust_method)
                logger.debug(f"{len(illusts)} illusts found, select {illust.title} ({illust.id}).")
                msg = await self.make_illust_msg(illust)
                await bot.send_msg(user_id=member_id, group_id=group_id, message=msg)
            else:
                if not no_error_msg:
                    await bot.send_msg(user_id=member_id, group_id=group_id, message="别看了，没有的。")
        except NoReplyError:
            pass
        except QueryError as e:
            if not no_error_msg:
                await bot.send_msg(user_id=member_id, group_id=group_id, message=e.reason)
            logger.warning(e)
        except TimeoutError as e:
            if not no_error_msg:
                await bot.send_msg(user_id=member_id, group_id=group_id, message="下载超时")
            logger.warning(e)
        except Exception as e:
            logger.exception(e)

    async def distribute_random_user_illust(self, user: typing.Union[str, int],
                                            bot: Bot,
                                            member_id: typing.Optional[int] = None,
                                            group_id: typing.Optional[int] = None,
                                            no_error_msg: bool = False):
        try:
            if isinstance(user, str):
                users = await self.data_source.search_user(user)
                if len(users) == 0:
                    await bot.send_msg(user_id=member_id, group_id=group_id, message="找不到相关用户")
                else:
                    user = users[0].id
            illusts = await self.data_source.user_illusts(user,
                                                          self.conf.pixiv_random_user_illust_max_item,
                                                          self.conf.pixiv_random_user_illust_max_page,
                                                          self.conf.pixiv_block_tags,
                                                          self.conf.pixiv_random_user_illust_min_bookmark,
                                                          self.conf.pixiv_random_user_illust_min_view)

            if len(illusts) > 0:
                illust = random_illust(illusts, self.conf.pixiv_random_illust_method)
                logger.debug(f"{len(illusts)} illusts found, select {illust.title} ({illust.id}).")
                msg = await self.make_illust_msg(illust)
                await bot.send_msg(user_id=member_id, group_id=group_id, message=msg)
            else:
                if not no_error_msg:
                    await bot.send_msg(user_id=member_id, group_id=group_id, message="别看了，没有的。")
        except NoReplyError:
            pass
        except QueryError as e:
            if not no_error_msg:
                await bot.send_msg(user_id=member_id, group_id=group_id, message=e.reason)
            logger.warning(e)
        except TimeoutError as e:
            if not no_error_msg:
                await bot.send_msg(user_id=member_id, group_id=group_id, message="下载超时")
            logger.warning(e)
        except Exception as e:
            logger.exception(e)

    async def distribute_random_recommended_illust(self, bot: Bot,
                                                   member_id: typing.Optional[int] = None,
                                                   group_id: typing.Optional[int] = None,
                                                   no_error_msg: bool = False):
        try:
            illusts = await self.data_source.recommended_illusts(self.conf.pixiv_random_recommended_illust_max_item,
                                                                 self.conf.pixiv_random_recommended_illust_max_page,
                                                                 self.conf.pixiv_block_tags,
                                                                 self.conf.pixiv_random_recommended_illust_min_bookmark,
                                                                 self.conf.pixiv_random_recommended_illust_min_view)

            if len(illusts) > 0:
                illust = random_illust(illusts, self.conf.pixiv_random_recommended_illust_method)
                logger.debug(f"{len(illusts)} illusts found, select {illust.title} ({illust.id}).")
                msg = await self.make_illust_msg(illust)
                await bot.send_msg(user_id=member_id, group_id=group_id, message=msg)
            else:
                if not no_error_msg:
                    await bot.send_msg(user_id=member_id, group_id=group_id, message="别看了，没有的。")
        except NoReplyError:
            pass
        except QueryError as e:
            if not no_error_msg:
                await bot.send_msg(user_id=member_id, group_id=group_id, message=e.reason)
            logger.warning(e)
        except TimeoutError as e:
            if not no_error_msg:
                await bot.send_msg(user_id=member_id, group_id=group_id, message="下载超时")
            logger.warning(e)
        except Exception as e:
            logger.exception(e)

    async def distribute_random_bookmark(self, bot: Bot,
                                         member_id: typing.Optional[int] = None,
                                         group_id: typing.Optional[int] = None,
                                         no_error_msg: bool = False):
        try:
            illusts = await self.data_source.user_bookmarks(self.conf.pixiv_random_bookmark_user_id,
                                                            self.conf.pixiv_random_bookmark_max_item,
                                                            self.conf.pixiv_random_bookmark_max_page,
                                                            self.conf.pixiv_block_tags,
                                                            self.conf.pixiv_random_bookmark_min_bookmark,
                                                            self.conf.pixiv_random_bookmark_min_view)

            if len(illusts) > 0:
                illust = random_illust(illusts, self.conf.pixiv_random_bookmark_method)
                logger.debug(f"{len(illusts)} illusts found, select {illust.title} ({illust.id}).")
                msg = await self.make_illust_msg(illust)
                await bot.send_msg(user_id=member_id, group_id=group_id, message=msg)
            else:
                if not no_error_msg:
                    await bot.send_msg(user_id=member_id, group_id=group_id, message="别看了，没有的。")
        except NoReplyError:
            pass
        except QueryError as e:
            if not no_error_msg:
                await bot.send_msg(user_id=member_id, group_id=group_id, message=e.reason)
            logger.warning(e)
        except TimeoutError as e:
            if not no_error_msg:
                await bot.send_msg(user_id=member_id, group_id=group_id, message="下载超时")
            logger.warning(e)
        except Exception as e:
            logger.exception(e)


distributor = Distributor(conf, data_source)

__all__ = ("Distributor", "distributor")
