import typing
from io import BytesIO

from nonebot.adapters.cqhttp import Message, MessageSegment

from .data_source import data_source
from .model.Illust import Illust


async def make_illust_msg(illust: Illust) -> Message:
    msg = Message()
    with BytesIO() as bio:
        if len(illust.meta_pages) > 0:
            url = illust.meta_pages[0].image_urls.original
        else:
            url = illust.meta_single_page.original_image_url
        bio.write(await data_source.download(illust.id, url))

        msg.append(MessageSegment.image(bio))
        msg.append(f"「{illust.title}」\n"
                   f"作者：{illust.user.name}\n"
                   f"https://www.pixiv.net/artworks/{illust.id}")
    return msg


async def make_illusts_msg(illusts: typing.List[Illust], num_start=1) -> Message:
    msg = Message()
    for i, illust in enumerate(illusts):
        with BytesIO() as bio:
            if len(illust.meta_pages) > 0:
                url = illust.meta_pages[0].image_urls.original
            else:
                url = illust.meta_single_page.original_image_url
            bio.write(await data_source.download(illust.id, url))

            msg.append(MessageSegment.image(bio))
            msg.append(f"#{i + num_start}「{illust.title}」\n"
                       f"作者：{illust.user.name}\n"
                       f"https://www.pixiv.net/artworks/{illust.id}")
    return msg
