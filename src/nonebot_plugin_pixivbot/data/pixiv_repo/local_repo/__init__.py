from nonebot import logger

from .base import LocalPixivRepo
from ....config import Config
from ....global_context import context

conf = context.require(Config)
if not conf.pixiv_use_local_cache:
    from .dummy import DummyPixivRepo

    context.bind(LocalPixivRepo, DummyPixivRepo)
    logger.info("local cache: disabled")
else:
    from .sql import SqlPixivRepo

    context.bind(LocalPixivRepo, SqlPixivRepo)
    logger.info(f"local cache: enabled ({conf.pixiv_sql_dialect})")

__all__ = ("LocalPixivRepo",)
