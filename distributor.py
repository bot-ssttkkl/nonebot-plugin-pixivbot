import typing

from nonebot import logger
from nonebot.adapters.cqhttp import Bot

from . import msg_maker
from .config import conf
from .data_source import data_source
from .errors import NoReplyError, QueryError
from .model.Illust import Illust
from .utils import random_illust


async def distribute_ranking(mode: typing.Optional[str],
                             range: typing.Optional[typing.Union[typing.Sequence[int], int]],
                             bot: Bot,
                             member_id: typing.Optional[int] = None,
                             group_id: typing.Optional[int] = None,
                             no_error_msg: bool = False):
    try:
        if mode is None:
            mode = conf.pixiv_ranking_default_mode

        if range is None:
            range = conf.pixiv_ranking_default_range

        if isinstance(range, int):
            num = range
            if num > conf.pixiv_ranking_fetch_item:
                await bot.send_msg(user_id=member_id, group_id=group_id,
                                   message=f'仅支持查询{conf.pixiv_ranking_fetch_item}名以内的插画')
            else:
                illusts = await data_source.illust_ranking(mode, conf.pixiv_ranking_fetch_item,
                                                           block_tags=conf.pixiv_block_tags)
                msg = await msg_maker.make_illust_msg(illusts[num - 1])
                await bot.send_msg(user_id=member_id, group_id=group_id, message=msg)
        else:
            start, end = range
            if end - start + 1 > conf.pixiv_ranking_max_item_per_msg:
                await bot.send_msg(user_id=member_id, group_id=group_id,
                                   message=f"仅支持一次查询{conf.pixiv_ranking_max_item_per_msg}张以下插画")
            elif start > end:
                await bot.send_msg(user_id=member_id, group_id=group_id,
                                   message="范围不合法")
            elif end > conf.pixiv_ranking_fetch_item:
                await bot.send_msg(user_id=member_id, group_id=group_id,
                                   message=f'仅支持查询{conf.pixiv_ranking_fetch_item}名以内的插画')
            else:
                illusts = await data_source.illust_ranking(mode)
                msg = await msg_maker.make_illusts_msg(illusts[start - 1:end], start)
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


async def distribute_illust(illust: typing.Union[int, Illust],
                            bot: Bot,
                            member_id: typing.Optional[int] = None,
                            group_id: typing.Optional[int] = None,
                            no_error_msg: bool = False):
    try:
        if isinstance(illust, int):
            illust = await data_source.illust_detail(illust)
        msg = await msg_maker.make_illust_msg(illust)
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


async def distribute_random_illust(word: str,
                                   bot: Bot,
                                   member_id: typing.Optional[int] = None,
                                   group_id: typing.Optional[int] = None,
                                   no_error_msg: bool = False):
    try:
        illusts = await data_source.search_illust(word,
                                                  conf.pixiv_random_illust_max_item,
                                                  conf.pixiv_random_illust_max_page,
                                                  conf.pixiv_block_tags,
                                                  conf.pixiv_random_illust_min_bookmark,
                                                  conf.pixiv_random_illust_min_view)

        if len(illusts) > 0:
            illust = random_illust(illusts, conf.pixiv_random_illust_method)
            logger.debug(f"{len(illusts)} illusts found, select {illust.title} ({illust.id}).")
            msg = await msg_maker.make_illust_msg(illust)
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


async def distribute_random_user_illust(user: typing.Union[str, int],
                                        bot: Bot,
                                        member_id: typing.Optional[int] = None,
                                        group_id: typing.Optional[int] = None,
                                        no_error_msg: bool = False):
    try:
        if isinstance(user, str):
            users = await data_source.search_user(user)
            if len(users) == 0:
                await bot.send_msg(user_id=member_id, group_id=group_id, message="找不到相关用户")
            else:
                user = users[0].id
        illusts = await data_source.user_illusts(user,
                                                 conf.pixiv_random_user_illust_max_item,
                                                 conf.pixiv_random_user_illust_max_page,
                                                 conf.pixiv_block_tags,
                                                 conf.pixiv_random_user_illust_min_bookmark,
                                                 conf.pixiv_random_user_illust_min_view)

        if len(illusts) > 0:
            illust = random_illust(illusts, conf.pixiv_random_illust_method)
            logger.debug(f"{len(illusts)} illusts found, select {illust.title} ({illust.id}).")
            msg = await msg_maker.make_illust_msg(illust)
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


async def distribute_random_recommended_illust(bot: Bot,
                                               member_id: typing.Optional[int] = None,
                                               group_id: typing.Optional[int] = None,
                                               no_error_msg: bool = False):
    try:
        illusts = await data_source.recommended_illusts(conf.pixiv_random_recommended_illust_max_item,
                                                        conf.pixiv_random_recommended_illust_max_page,
                                                        conf.pixiv_block_tags,
                                                        conf.pixiv_random_recommended_illust_min_bookmark,
                                                        conf.pixiv_random_recommended_illust_min_view)

        if len(illusts) > 0:
            illust = random_illust(illusts, conf.pixiv_random_recommended_illust_method)
            logger.debug(f"{len(illusts)} illusts found, select {illust.title} ({illust.id}).")
            msg = await msg_maker.make_illust_msg(illust)
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


async def distribute_random_bookmark(bot: Bot,
                                     member_id: typing.Optional[int] = None,
                                     group_id: typing.Optional[int] = None,
                                     no_error_msg: bool = False):
    try:
        illusts = await data_source.user_bookmarks(conf.pixiv_random_bookmark_user_id,
                                                   conf.pixiv_random_bookmark_max_item,
                                                   conf.pixiv_random_bookmark_max_page,
                                                   conf.pixiv_block_tags,
                                                   conf.pixiv_random_bookmark_min_bookmark,
                                                   conf.pixiv_random_bookmark_min_view)

        if len(illusts) > 0:
            illust = random_illust(illusts, conf.pixiv_random_bookmark_method)
            logger.debug(f"{len(illusts)} illusts found, select {illust.title} ({illust.id}).")
            msg = await msg_maker.make_illust_msg(illust)
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
