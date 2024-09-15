from collections.abc import Sequence
from functools import partial
from pathlib import Path
from typing import Optional, List, Literal, Any, Dict
from urllib.parse import urlparse

import nonebot_plugin_localstore as store
from nonebot import logger
from nonebot.compat import PYDANTIC_V2
from pydantic import conlist
from ssttkkl_nonebot_utils.config_loader import BaseSettings, load_conf

from .enums import *
from .enums import RandomIllustMethod
from .global_context import context


def _get_default_sql_conn_url():
    # 旧版本的sqlite数据库在working directory
    data_file = Path("pixiv_bot.db")
    if not data_file.exists():
        data_file = store.get_data_file("nonebot_plugin_pixivbot", "pixiv_bot.db")

    return "sqlite+aiosqlite:///" + str(data_file)


def compatible_model_pre_validator(func):
    if PYDANTIC_V2:
        from pydantic import model_validator

        @model_validator(mode='before')
        @classmethod
        def checker(cls, values: dict[str]):
            return func(cls, values)

        return checker
    else:
        from pydantic import root_validator
        return root_validator(pre=True, allow_reuse=True)(func)


def compatible_field_validator(*fields: str):
    def wrapper(func):
        if PYDANTIC_V2:
            from pydantic import field_validator
            from pydantic_core.core_schema import ValidationInfo

            @field_validator(*fields)
            @classmethod
            def checker(cls, v: str, info: ValidationInfo):
                return func(cls, v, info.data, {"name": info.field_name})

            return checker
        else:
            from pydantic import validator
            from pydantic.fields import ModelField

            @validator(*fields, allow_reuse=True)
            def checker(cls, v: str, values: Dict[str, Any], field: ModelField):
                return func(cls, v, values, {"name": field.name})

            return checker

    return wrapper


class Config(BaseSettings):
    @compatible_model_pre_validator
    def deprecated_access_control_config(cls, values: Dict[str, Any]):
        for name in {"blacklist", "pixiv_query_cooldown", "pixiv_no_query_cooldown_users"}:
            if name in values:
                logger.warning(f"config \"{name}\" is deprecated, use nonebot-plugin-access-control instead "
                               "(MORE INFO: https://github.com/ssttkkl/nonebot-plugin-pixivbot#%E6%9D%83%E9%99%90%E6%8E%A7%E5%88%B6)")
        return values

    @compatible_model_pre_validator
    def deprecated_mongodb_config(cls, values: Dict[str, Any]):
        if values.get("pixiv_data_source", "sql") == "mongo" or "pixiv_mongo_conn_url" in values:
            logger.warning("mongo support was removed, use sql instead")
        return values

    pixiv_refresh_token: str

    pixiv_sql_conn_url: str = _get_default_sql_conn_url()

    @property
    def pixiv_sql_dialect(self) -> str:
        url = urlparse(self.pixiv_sql_conn_url)
        if '+' in url.scheme:
            pixiv_sql_dialect = url.scheme.split('+')[0]
        else:
            pixiv_sql_dialect = url.scheme
        return pixiv_sql_dialect

    pixiv_use_local_cache: bool = True
    pixiv_local_cache_type: Literal["sql", "file"] = "file"

    pixiv_proxy: Optional[str] = None
    pixiv_query_timeout: float = 60.0
    pixiv_loading_prompt_delayed_time: float = 5.0
    pixiv_simultaneous_query: int = 8

    pixiv_download_cache_expires_in: int = 3600 * 24 * 7
    pixiv_illust_detail_cache_expires_in: int = 3600 * 24 * 7
    pixiv_user_detail_cache_expires_in: int = 3600 * 24 * 7
    pixiv_illust_ranking_cache_expires_in: int = 3600 * 6
    pixiv_search_illust_cache_expires_in: int = 3600 * 24
    pixiv_search_illust_cache_delete_in: int = 3600 * 24 * 30
    pixiv_search_user_cache_expires_in: int = 3600 * 24
    pixiv_search_user_cache_delete_in: int = 3600 * 24 * 30
    pixiv_user_illusts_cache_expires_in: int = 3600 * 24
    pixiv_user_illusts_cache_delete_in: int = 3600 * 24 * 30
    pixiv_user_bookmarks_cache_expires_in: int = 3600 * 24
    pixiv_user_bookmarks_cache_delete_in: int = 3600 * 24 * 30
    pixiv_related_illusts_cache_expires_in: int = 3600 * 24
    pixiv_other_cache_expires_in: int = 3600 * 6

    pixiv_block_tags: List[str] = []
    pixiv_block_action: BlockAction = BlockAction.no_image

    pixiv_exclude_ai_illusts: bool = False

    pixiv_download_custom_domain: Optional[str] = None

    pixiv_compression_enabled: bool = False
    pixiv_compression_max_size: Optional[int] = None
    pixiv_compression_quantity: Optional[float] = None

    # 不加allow_reuse跑pytest会报错
    @compatible_field_validator('pixiv_compression_max_size', 'pixiv_compression_quantity')
    def compression_validator(cls, v, values, field: dict):
        if values['pixiv_compression_enabled'] and v is None:
            raise ValueError(
                f'pixiv_compression_enabled is True but {field["name"]} got None.')
        return v

    pixiv_query_to_me_only: bool = False
    pixiv_command_to_me_only: bool = False

    pixiv_poke_action: Literal[
        "", "ranking", "random_recommended_illust", "random_bookmark"] = "random_recommended_illust"

    pixiv_send_illust_link: bool = False
    pixiv_send_forward_message: Literal['always', 'auto', 'never'] = 'auto'

    pixiv_max_item_per_query: int = 10
    pixiv_max_page_per_illust: int = 10

    pixiv_tag_translation_enabled: bool = True

    pixiv_more_enabled: bool = True
    pixiv_query_expires_in: int = 10 * 60

    pixiv_illust_query_enabled: bool = True
    pixiv_illust_sniffer_enabled: bool = True

    pixiv_ranking_query_enabled: bool = True
    pixiv_ranking_default_mode: RankingMode = RankingMode.day
    pixiv_ranking_default_range: Sequence[int] = [1, 3]
    pixiv_ranking_fetch_item: int = 150
    pixiv_ranking_max_item_per_query: int = 10

    @compatible_field_validator('pixiv_ranking_default_range')
    def ranking_default_range_validator(cls, v, values, field: dict):
        if len(v) != 2 or v[0] > v[1]:
            raise ValueError(f'illegal {field["name"]} value: {v}')
        return v

    pixiv_random_illust_query_enabled: bool = True
    pixiv_random_illust_method: RandomIllustMethod = RandomIllustMethod.bookmark_proportion
    pixiv_random_illust_min_bookmark: int = 0
    pixiv_random_illust_min_view: int = 0
    pixiv_random_illust_max_page: int = 20
    pixiv_random_illust_max_item: int = 500

    pixiv_random_recommended_illust_query_enabled: bool = True
    pixiv_random_recommended_illust_method: RandomIllustMethod = RandomIllustMethod.uniform
    pixiv_random_recommended_illust_min_bookmark: int = 0
    pixiv_random_recommended_illust_min_view: int = 0
    pixiv_random_recommended_illust_max_page: int = 40
    pixiv_random_recommended_illust_max_item: int = 1000

    pixiv_random_related_illust_query_enabled: bool = True
    pixiv_random_related_illust_method: RandomIllustMethod = RandomIllustMethod.bookmark_proportion
    pixiv_random_related_illust_min_bookmark: int = 0
    pixiv_random_related_illust_min_view: int = 0
    pixiv_random_related_illust_max_page: int = 4
    pixiv_random_related_illust_max_item: int = 100

    pixiv_random_user_illust_query_enabled: bool = True
    pixiv_random_user_illust_method: RandomIllustMethod = RandomIllustMethod.timedelta_proportion
    pixiv_random_user_illust_min_bookmark: int = 0
    pixiv_random_user_illust_min_view: int = 0
    pixiv_random_user_illust_max_page: int = 2 ** 31
    pixiv_random_user_illust_max_item: int = 2 ** 31

    pixiv_random_bookmark_query_enabled: bool = True
    pixiv_random_bookmark_user_id: Optional[int] = None
    pixiv_random_bookmark_method: RandomIllustMethod = RandomIllustMethod.uniform
    pixiv_random_bookmark_min_bookmark: int = 0
    pixiv_random_bookmark_min_view: int = 0
    pixiv_random_bookmark_max_page: int = 2 ** 31
    pixiv_random_bookmark_max_item: int = 2 ** 31

    pixiv_random_following_illust_query_enabled: bool = True
    pixiv_random_following_illust_method: RandomIllustMethod = RandomIllustMethod.timedelta_proportion
    pixiv_random_following_illust_min_bookmark: int = 0
    pixiv_random_following_illust_min_view: int = 0
    pixiv_random_following_illust_max_page: int = 2 ** 31
    pixiv_random_following_illust_max_item: int = 2 ** 31

    pixiv_watch_interval: int = 600

    access_control_reply_on_permission_denied: Optional[str] = None
    access_control_reply_on_rate_limited: Optional[str] = None

    class Config:
        extra = "ignore"


context.register_lazy(Config, partial(load_conf, Config))

__all__ = ("Config",)
