from io import StringIO
from typing import Optional

from nonebot_plugin_pixivbot.model.message import IllustMessageModel
from .card_builder import CardBuilder


def make_illust_card(model: IllustMessageModel, image_url: Optional[str], block_msg: Optional[str]):
    builder = CardBuilder()

    if model.header:
        builder.header(model.header)

    if image_url:
        builder.image_container(image_url)

    if block_msg:
        builder.section(block_msg)

    with StringIO() as sio:
        if model.number is not None:
            sio.write(f"#{model.number}")

        sio.write(f"「{model.title}」")
        if model.total != 1:
            sio.write(f"（{model.page + 1}/{model.total}）")
        sio.write("\n")

        sio.write(f"作者：{model.author}\n"
                  f"发布时间：{model.create_time}\n")
        builder.section(sio.getvalue())

    builder.section(f"[{model.link}]({model.link})", "kmarkdown")
    return builder.build()
