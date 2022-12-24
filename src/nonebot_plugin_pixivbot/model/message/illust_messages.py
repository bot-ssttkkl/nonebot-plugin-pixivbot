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
                           number: Optional[int] = None,
                           block_r18: bool = False,
                           block_r18g: bool = False) -> Optional["IllustMessagesModel"]:
        tasks = [
            create_task(
                IllustMessageModel.from_illust(x, number=number + i if number is not None else None,
                                               block_r18=block_r18, block_r18g=block_r18g)
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

    @staticmethod
    async def from_illust(illust: Illust, *,
                          header: Optional[str] = None,
                          number: Optional[int] = None,
                          max_page: Optional[int] = 2 ** 31 - 1,
                          block_r18: bool = False,
                          block_r18g: bool = False) -> Optional["IllustMessagesModel"]:
        tasks = [
            create_task(
                IllustMessageModel.from_illust(illust, page=i, number=number,
                                               block_r18=block_r18, block_r18g=block_r18g)
            ) for i in range(min(illust.page_count, max_page))
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
