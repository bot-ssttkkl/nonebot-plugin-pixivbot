from asyncio import create_task, gather
from typing import Optional, Sequence

from pydantic import BaseModel

from nonebot_plugin_pixivbot.model import Illust
from nonebot_plugin_pixivbot.model.message.illust_message import IllustMessageModel


class IllustMessagesModel(BaseModel):
    header: Optional[str] = None
    messages: Sequence[IllustMessageModel]

    @staticmethod
    async def from_illusts(illusts: Sequence[Illust], *,
                           header: Optional[str] = None,
                           number: Optional[int] = None) -> Optional["IllustMessagesModel"]:
        tasks = [
            create_task(
                IllustMessageModel.from_illust(x, number=number + i if number is not None else None)
            ) for i, x in enumerate(illusts)
        ]
        await gather(*tasks)

        messages = []
        for t in tasks:
            result = await t
            if result:
                messages.append(result)

        model = IllustMessagesModel(header=header, messages=messages)
        return model

    def flat(self):
        for x in self.messages:
            yield x.copy(update={"header": self.header})

    def flat_first(self) -> IllustMessageModel:
        for x in self.flat():
            return x
