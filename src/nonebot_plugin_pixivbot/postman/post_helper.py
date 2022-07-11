from typing import Optional, Sequence

from nonebot_plugin_pixivbot.global_context import context as context
from nonebot_plugin_pixivbot.model import Illust
from nonebot_plugin_pixivbot.postman import Postman, PostDestination
from nonebot_plugin_pixivbot.postman.model.illust_message import IllustMessageModel
from nonebot_plugin_pixivbot.postman.model.illust_messages import IllustMessagesModel

postman = context.require(Postman)


async def post_illust(illust: Illust, *,
                      header: Optional[str] = None,
                      number: Optional[int] = None,
                      post_dest: PostDestination):
    model = IllustMessageModel.from_illust(illust)
    if model is not None:
        await postman.send_illust(model, header=header, number=number, post_dest=post_dest)


async def post_illusts(illusts: Sequence[Illust], *,
                       header: Optional[str] = None,
                       number: Optional[int] = None,
                       post_dest: PostDestination):
    messages = map(lambda x: IllustMessageModel.from_illust(x[1], number=number + x[0]), enumerate(illusts))
    messages = filter(lambda x: x is not None, messages)
    messages = list(messages)

    model = IllustMessagesModel(header=header, messages=messages)
    await postman.send_illusts(model, post_dest=post_dest)


__all__ = ("post_illust", "post_illusts")
