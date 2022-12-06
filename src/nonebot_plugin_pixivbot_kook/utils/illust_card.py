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

    content = f"「{model.title}」\n作者：{model.author}\n发布时间：{model.create_time}\n"
    if model.number is not None:
        content = f"#{model.number} {content}"
    builder.section(content)

    builder.section(f"[{model.link}]({model.link})", "kmarkdown")
    return builder.build()
