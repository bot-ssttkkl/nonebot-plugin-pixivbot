from pathlib import Path
from typing import Optional, List, Literal
from urllib.parse import urlparse

from nonebot import get_driver, logger, require
from pydantic import BaseSettings, validator, root_validator
from pydantic.fields import ModelField

require("nonebot_plugin_localstore")

import nonebot_plugin_localstore as store

from .enums import *
from .global_context import context


def _get_default_sql_conn_url():
    # 旧版本的sqlite数据库在working directory
    data_file = Path("pixiv_bot.db")
    if not data_file.exists():
        data_file = store.get_data_file("nonebot_plugin_pixivbot", "pixiv_bot.db")

    return "sqlite+aiosqlite:///" + str(data_file)


@context.register_singleton(**get_driver().config.dict())
class Config(BaseSettings):
    @root_validator(pre=True, allow_reuse=True)
    def deprecated_access_control_config(cls, values):
        for name in {"blacklist", "pixiv_query_cooldown", "pixiv_no_query_cooldown_users"}:
            if name in values:
                logger.warning(f"config \"{name}\" is deprecated, use nonebot-plugin-access-control instead "
                               "(MORE INFO: https://github.com/ssttkkl/nonebot-plugin-pixivbot#%E6%9D%83%E9%99%90%E6%8E%A7%E5%88%B6)")
        return values

    @root_validator(pre=True, allow_reuse=True)
    def deprecated_mongodb_config(cls, values):
        if values.get("pixiv_data_source", "sql") == "mongo" or "pixiv_mongo_conn_url" in values:
            logger.warning("mongo support was removed, use sql instead")
        return values

    pixiv_refresh_token: str

    pixiv_sql_conn_url: str
    pixiv_sql_dialect: str
    pixiv_use_local_cache: bool = True

    @root_validator(pre=True, allow_reuse=True)
    def default_sql_conn_url(cls, values):
        if "pixiv_sql_conn_url" not in values:
            values["pixiv_sql_conn_url"] = _get_default_sql_conn_url()
        return values

    @root_validator(pre=True, allow_reuse=True)
    def detect_sql_dialect(cls, values):
        values["pixiv_mongo_conn_url"] = ""
        values["pixiv_mongo_database_name"] = ""

        url = urlparse(values["pixiv_sql_conn_url"])
        if '+' in url.scheme:
            pixiv_sql_dialect = url.scheme.split('+')[0]
        else:
            pixiv_sql_dialect = url.scheme
        values["pixiv_sql_dialect"] = pixiv_sql_dialect

        return values

    pixiv_proxy: Optional[str]
    pixiv_query_timeout: float = 60.0
    pixiv_loading_prompt_delayed_time: float = 5.0
    pixiv_simultaneous_query: int = 8

    pixiv_download_cache_expires_in = 3600 * 24 * 7
    pixiv_illust_detail_cache_expires_in = 3600 * 24 * 7
    pixiv_user_detail_cache_expires_in = 3600 * 24 * 7
    pixiv_illust_ranking_cache_expires_in = 3600 * 6
    pixiv_search_illust_cache_expires_in = 3600 * 24
    pixiv_search_illust_cache_delete_in = 3600 * 24 * 30
    pixiv_search_user_cache_expires_in = 3600 * 24
    pixiv_search_user_cache_delete_in = 3600 * 24 * 30
    pixiv_user_illusts_cache_expires_in = 3600 * 24
    pixiv_user_illusts_cache_delete_in = 3600 * 24 * 30
    pixiv_user_bookmarks_cache_expires_in = 3600 * 24
    pixiv_user_bookmarks_cache_delete_in = 3600 * 24 * 30
    pixiv_related_illusts_cache_expires_in = 3600 * 24
    pixiv_other_cache_expires_in = 3600 * 6

    pixiv_block_tags: List[str] = []
    pixiv_block_action: BlockAction = BlockAction.no_image

    pixiv_exclude_ai_illusts: bool = False

    pixiv_download_custom_domain: Optional[str]

    pixiv_compression_enabled: bool = False
    pixiv_compression_max_size: Optional[int]
    pixiv_compression_quantity: Optional[float]

    # 不加allow_reuse跑pytest会报错
    @validator('pixiv_compression_max_size', 'pixiv_compression_quantity', allow_reuse=True)
    def compression_validator(cls, v, values, field: ModelField):
        if values['pixiv_compression_enabled'] and v is None:
            raise ValueError(
                f'pixiv_compression_enabled is True but {field.name} got None.')
        return v

    pixiv_query_to_me_only = False
    pixiv_command_to_me_only = False

    pixiv_poke_action: Literal[
        "", "ranking", "random_recommended_illust", "random_bookmark"] = "random_recommended_illust"

    pixiv_send_illust_link: bool = False
    pixiv_send_forward_message: Literal['always', 'auto', 'never'] = 'auto'

    pixiv_max_item_per_query = 10

    pixiv_tag_translation_enabled = True

    pixiv_more_enabled = True
    pixiv_query_expires_in = 10 * 60

    pixiv_illust_query_enabled = True
    pixiv_illust_sniffer_enabled = True

    pixiv_ranking_query_enabled = True
    pixiv_ranking_default_mode: RankingMode = RankingMode.day
    pixiv_ranking_default_range = [1, 3]
    pixiv_ranking_fetch_item = 150
    pixiv_ranking_max_item_per_query = 10

    @validator('pixiv_ranking_default_range', allow_reuse=True)
    def ranking_default_range_validator(cls, v, field: ModelField):
        if len(v) < 2 or v[0] > v[1]:
            raise ValueError(f'illegal {field.name} value: {v}')
        return v

    pixiv_random_illust_query_enabled = True
    pixiv_random_illust_method = RandomIllustMethod.bookmark_proportion
    pixiv_random_illust_min_bookmark = 0
    pixiv_random_illust_min_view = 0
    pixiv_random_illust_max_page = 20
    pixiv_random_illust_max_item = 500

    pixiv_random_recommended_illust_query_enabled = True
    pixiv_random_recommended_illust_method = RandomIllustMethod.uniform
    pixiv_random_recommended_illust_min_bookmark = 0
    pixiv_random_recommended_illust_min_view = 0
    pixiv_random_recommended_illust_max_page = 40
    pixiv_random_recommended_illust_max_item = 1000

    pixiv_random_related_illust_query_enabled = True
    pixiv_random_related_illust_method = RandomIllustMethod.bookmark_proportion
    pixiv_random_related_illust_min_bookmark = 0
    pixiv_random_related_illust_min_view = 0
    pixiv_random_related_illust_max_page = 4
    pixiv_random_related_illust_max_item = 100

    pixiv_random_user_illust_query_enabled = True
    pixiv_random_user_illust_method = RandomIllustMethod.timedelta_proportion
    pixiv_random_user_illust_min_bookmark = 0
    pixiv_random_user_illust_min_view = 0
    pixiv_random_user_illust_max_page = 2 ** 31
    pixiv_random_user_illust_max_item = 2 ** 31

    pixiv_random_bookmark_query_enabled = True
    pixiv_random_bookmark_user_id: Optional[int] = None
    pixiv_random_bookmark_method = RandomIllustMethod.uniform
    pixiv_random_bookmark_min_bookmark = 0
    pixiv_random_bookmark_min_view = 0
    pixiv_random_bookmark_max_page = 2 ** 31
    pixiv_random_bookmark_max_item = 2 ** 31

    pixiv_random_following_illust_query_enabled = True
    pixiv_random_following_illust_method = RandomIllustMethod.timedelta_proportion
    pixiv_random_following_illust_min_bookmark = 0
    pixiv_random_following_illust_min_view = 0
    pixiv_random_following_illust_max_page = 2 ** 31
    pixiv_random_following_illust_max_item = 2 ** 31

    pixiv_watch_interval = 600

    access_control_reply_on_permission_denied: Optional[str]
    access_control_reply_on_rate_limited: Optional[str]

    class Config:
        extra = "ignore"


__all__ = ("Config",)
