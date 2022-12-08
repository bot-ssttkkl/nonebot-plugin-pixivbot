from typing import Generic

from pydantic.generics import GenericModel

from nonebot_plugin_pixivbot.model import T_UID, T_GID, PostIdentifier


class IntervalTask(GenericModel, Generic[T_UID, T_GID]):
    code: str = ""
    subscriber: PostIdentifier[T_UID, T_GID]
