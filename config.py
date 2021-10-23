import typing

from nonebot import get_driver
from pydantic import BaseSettings, validator
from pydantic.fields import ModelField


class Config(BaseSettings):
    pixiv_refresh_token: str
    pixiv_mongo_conn_url: str
    pixiv_mongo_database_name: str
    pixiv_proxy: typing.Optional[str]
    pixiv_query_timeout: int = 60

    pixiv_block_tags: typing.List[str] = []
    pixiv_block_action: str = "no_image"

    @validator('pixiv_block_action')
    def block_action_validator(cls, v, field: ModelField):
        if v not in ['no_image', 'completely_block', 'no_reply']:
            raise ValueError(f'pixiv_compression_enabled is True but {field.name} got None.')
        return v

    pixiv_download_quantity: str = "original"
    pixiv_download_custom_domain: typing.Optional[str]

    @validator('pixiv_download_quantity')
    def download_quantity_validator(cls, v, field: ModelField):
        if v not in ['original', 'square_medium', 'medium', 'large']:
            raise ValueError(f'pixiv_compression_enabled is True but {field.name} got None.')
        return v

    pixiv_compression_enabled: bool = False
    pixiv_compression_max_size: typing.Optional[int]
    pixiv_compression_quantity: typing.Optional[float]

    @validator('pixiv_compression_max_size', 'pixiv_compression_quantity')
    def compression_validator(cls, v, values, field: ModelField):
        if values['pixiv_compression_enabled'] and v is None:
            raise ValueError(f'pixiv_compression_enabled is True but {field.name} got None.')
        return v

    # pixiv_illust_query_permission = {
    #     "group": [491959457],
    #     "friend": "all"
    # }
    #
    # @validator('pixiv_illust_query_permission')
    # def query_permission_validator(cls, v, field: ModelField):
    #     if v is not None and not isinstance(v, dict):
    #         raise ValueError(f'{field} expected a dict, but got a {type(v)}.')
    #     if "group" in v:
    #         if isinstance(v["group"], list):
    #             for i, x in enumerate(v["group"]):
    #                 if not isinstance(x, int):
    #                     raise ValueError(f'{field}["group"][{i}] expected a int, but got a {type(x)}.')
    #         elif v["group"] != "all":
    #             raise ValueError(f'{field}["group"] expected "all" or a list, but got a {type(v["group"])}.')
    #     if "friend" in v:
    #         if isinstance(v["friend"], list):
    #             for i, x in enumerate(v["group"]):
    #                 if not isinstance(x, int):
    #                     raise ValueError(f'{field}["friend"][{i}] expected a int, but got a {type(x)}.')
    #         elif v["friend"] != "all":
    #             raise ValueError(f'{field}["friend"] expected "all" or a list, but got a {type(v["friend"])}.')

    pixiv_query_cooldown = 0
    pixiv_no_query_cooldown_users = []

    pixiv_illust_query_enabled = True

    pixiv_ranking_query_enabled = True
    pixiv_ranking_default_mode = "day"
    pixiv_ranking_default_range = [1, 3]
    pixiv_ranking_fetch_item = 150
    pixiv_ranking_max_item_per_msg = 5

    @validator('pixiv_ranking_default_mode')
    def ranking_default_mode_validator(cls, v, field: ModelField):
        if v not in ['day', 'week', 'month', 'day_male', 'day_female', 'week_original', 'week_rookie', 'day_manga']:
            raise ValueError(f'illegal {field.name} value: {v}')
        return v

    @validator('pixiv_ranking_default_range')
    def ranking_default_range_validator(cls, v, field: ModelField):
        if len(v) < 2 or v[0] > v[1]:
            raise ValueError(f'illegal {field.name} value: {v}')
        return v

    pixiv_random_illust_query_enabled = True
    pixiv_random_illust_method = "bookmark_proportion"
    pixiv_random_illust_min_bookmark = 0
    pixiv_random_illust_min_view = 0
    pixiv_random_illust_max_page = 20
    pixiv_random_illust_max_item = 500

    pixiv_random_recommended_illust_query_enabled = True
    pixiv_random_recommended_illust_method = "uniform"
    pixiv_random_recommended_illust_min_bookmark = 0
    pixiv_random_recommended_illust_min_view = 0
    pixiv_random_recommended_illust_max_page = 40
    pixiv_random_recommended_illust_max_item = 1000

    pixiv_random_user_illust_query_enabled = True
    pixiv_random_user_illust_method = "timedelta_proportion"
    pixiv_random_user_illust_min_bookmark = 0
    pixiv_random_user_illust_min_view = 0
    pixiv_random_user_illust_max_page = 2 ** 31
    pixiv_random_user_illust_max_item = 2 ** 31

    pixiv_random_bookmark_query_enabled = True
    pixiv_random_bookmark_user_id = 0
    pixiv_random_bookmark_method = "uniform"
    pixiv_random_bookmark_min_bookmark = 0
    pixiv_random_bookmark_min_view = 0
    pixiv_random_bookmark_max_page = 2 ** 31
    pixiv_random_bookmark_max_item = 2 ** 31

    @validator('pixiv_random_illust_method', 'pixiv_random_recommended_illust_method',
               'pixiv_random_user_illust_method', 'pixiv_random_bookmark_method')
    def random_method_validator(cls, v, field: ModelField):
        if v not in ['bookmark_proportion', 'view_proportion', 'timedelta_proportion', 'uniform']:
            raise ValueError(f'illegal {field.name} value: {v}')
        return v

    pixiv_poke_action: typing.Optional[str] = "random_recommended_illust"

    @validator('pixiv_poke_action')
    def pixiv_poke_action_validator(cls, v, field: ModelField):
        if v not in [None, "", "ranking", "random_recommended_illust", "random_bookmark"]:
            raise ValueError(f'illegal {field.name} value: {v}')
        return v

    class Config:
        extra = "ignore"


_global_config = get_driver().config
conf = Config(**_global_config.dict())

__all__ = ("Config", "conf")
