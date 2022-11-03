from typing import Generic

from pydantic.generics import GenericModel

from nonebot_plugin_pixivbot.model import T_UID


class PixivBinding(GenericModel, Generic[T_UID]):
    adapter: str
    user_id: T_UID
    pixiv_user_id: int
