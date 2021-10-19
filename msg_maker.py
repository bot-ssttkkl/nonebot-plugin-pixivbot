import typing
from io import BytesIO

from nonebot.adapters.cqhttp import Message, MessageSegment

from .config import conf
from .data_source import data_source
from .errors import NoReplyError
from .model.Illust import Illust


async def make_illust_msg(illust: Illust) -> Message:
    msg = Message()

    if illust.has_tags(conf.pixiv_block_tags):
        if conf.pixiv_block_action == "no_image":
            msg.append("该画像因含有不可描述的tag而被自主规制\n")
            msg.append(f"「{illust.title}」\n"
                       f"作者：{illust.user.name}\n"
                       f"https://www.pixiv.net/artworks/{illust.id}")
        elif conf.pixiv_block_action == "completely_block":
            msg.append("该画像因含有不可描述的tag而被自主规制\n")
        elif conf.pixiv_block_action == "no_reply":
            raise NoReplyError()
    else:
        with BytesIO() as bio:
            bio.write(await data_source.download(illust))

            msg.append(MessageSegment.image(bio))
            msg.append(f"「{illust.title}」\n"
                       f"作者：{illust.user.name}\n"
                       f"https://www.pixiv.net/artworks/{illust.id}")
        return msg


async def make_illusts_msg(illusts: typing.List[Illust], num_start=1) -> Message:
    msg = Message()
    for i, illust in enumerate(illusts):
        if illust.has_tags(conf.pixiv_block_tags):
            if conf.pixiv_block_action == "no_image":
                msg.append("该画像因含有不可描述的tag而被自主规制\n")
                msg.append(f"#{i + num_start}「{illust.title}」\n"
                           f"作者：{illust.user.name}\n"
                           f"https://www.pixiv.net/artworks/{illust.id}")
            elif conf.pixiv_block_action == "completely_block":
                msg.append("该画像因含有不可描述的tag而被自主规制\n")
            elif conf.pixiv_block_action == "no_reply":
                raise NoReplyError()
        else:
            with BytesIO() as bio:
                bio.write(await data_source.download(illust))

                msg.append(MessageSegment.image(bio))
                msg.append(f"#{i + num_start}「{illust.title}」\n"
                           f"作者：{illust.user.name}\n"
                           f"https://www.pixiv.net/artworks/{illust.id}")
    return msg
