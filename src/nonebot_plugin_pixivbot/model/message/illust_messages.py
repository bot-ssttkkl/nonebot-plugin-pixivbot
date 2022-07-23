from typing import Optional, Sequence

from pydantic import BaseModel

from nonebot_plugin_pixivbot.model.message.illust_message import IllustMessageModel


class IllustMessagesModel(BaseModel):
    header: Optional[str] = None
    messages: Sequence[IllustMessageModel]

    def flat(self):
        for x in self.messages:
            yield x.copy(update={"header": self.header})

    def flat_first(self) -> IllustMessageModel:
        for x in self.flat():
            return x
