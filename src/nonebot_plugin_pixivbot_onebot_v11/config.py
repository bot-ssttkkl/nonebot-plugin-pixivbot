from typing import Optional, Literal

from nonebot import get_driver
from pydantic import validator, BaseSettings
from pydantic.fields import ModelField

from nonebot_plugin_pixivbot.global_context import context


@context.register_singleton(**get_driver().config.dict())
class OnebotV11Config(BaseSettings):
    pixiv_poke_action: Optional[str] = "random_recommended_illust"
    pixiv_onebot_with_link: bool = False
    pixiv_onebot_send_forward_message: Literal['always', 'auto', 'never'] = 'auto'

    @validator('pixiv_poke_action', allow_reuse=True)
    def pixiv_poke_action_validator(cls, v, field: ModelField):
        if v not in [None, "", "ranking", "random_recommended_illust", "random_bookmark"]:
            raise ValueError(f'illegal {field.name} value: {v}')
        return v

    class Config:
        extra = "ignore"


__all__ = ("OnebotV11Config",)
