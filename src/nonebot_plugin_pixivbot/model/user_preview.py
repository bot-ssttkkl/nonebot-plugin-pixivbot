from typing import List

from pydantic import BaseModel

from nonebot_plugin_pixivbot.model import User, Illust


class UserPreview(BaseModel):
    user: User
    illusts: List[Illust]

    class Config:
        extra = "ignore"
