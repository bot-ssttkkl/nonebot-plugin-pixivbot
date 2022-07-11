from typing import Optional, Sequence

from pydantic import BaseModel

from nonebot_plugin_pixivbot.postman.model.illust_message import IllustMessageModel


class IllustMessagesModel(BaseModel):
    header: Optional[str] = None
    messages: Sequence[IllustMessageModel]

    def flat_first(self) -> IllustMessageModel:
        return self.messages[0].copy(update={"header": self.header})
