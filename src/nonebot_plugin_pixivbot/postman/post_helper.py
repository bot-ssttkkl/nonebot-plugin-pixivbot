from asyncio import create_task, wait
from typing import Optional, Sequence

from nonebot_plugin_pixivbot.global_context import context as context
from nonebot_plugin_pixivbot.model import Illust
from nonebot_plugin_pixivbot.postman.model.illust_message import IllustMessageModel
from nonebot_plugin_pixivbot.postman.model.illust_messages import IllustMessagesModel
from nonebot_plugin_pixivbot.postman.post_destination import PostDestination
from nonebot_plugin_pixivbot.postman.postman import Postman


async def post_illust(illust: Illust, *,
                      header: Optional[str] = None,
                      number: Optional[int] = None,
                      post_dest: PostDestination):
    postman = context.require(Postman)
    model = await IllustMessageModel.from_illust(illust, header=header, number=number)
    if model is not None:
        await postman.send_illust(model, post_dest=post_dest)


async def post_illusts(illusts: Sequence[Illust], *,
                       header: Optional[str] = None,
                       number: Optional[int] = None,
                       post_dest: PostDestination):
    postman = context.require(Postman)
    tasks = [
        create_task(
            IllustMessageModel.from_illust(x, number=number + i if number is not None else None)
        ) for i, x in enumerate(illusts)
    ]
    await wait(tasks)

    messages = []
    for t in tasks:
        result = await t
        if result:
            messages.append(result)

    model = IllustMessagesModel(header=header, messages=messages)
    await postman.send_illusts(model, post_dest=post_dest)


__all__ = ("post_illust", "post_illusts")
