from io import BytesIO

from nonebot.adapters.cqhttp import Message, MessageSegment

from .model.Illust import Illust
from .data_source import data_source


async def make_illust_msg(illust: Illust) -> Message:
    with BytesIO() as bio:
        if len(illust.meta_pages) > 0:
            url = illust.meta_pages[0].image_urls.original
        else:
            url = illust.meta_single_page.original_image_url
        bio.write(await data_source.download(illust.id, url))

        msg = Message.template("{} \n「{}」{}\n{}").format(
            MessageSegment.image(bio),
            illust.title,
            illust.user.name,
            f"https://www.pixiv.net/artworks/{illust.id}"
        )
        return msg
