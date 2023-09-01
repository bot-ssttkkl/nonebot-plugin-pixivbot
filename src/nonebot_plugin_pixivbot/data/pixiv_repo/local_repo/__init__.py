from nonebot import logger

from .base import LocalPixivRepo
from ....config import Config
from ....global_context import context

conf = context.require(Config)
if not conf.pixiv_use_local_cache:
    from .dummy import DummyPixivRepo

    context.bind(LocalPixivRepo, DummyPixivRepo)
    logger.info("local cache: disabled")
elif conf.pixiv_local_cache_type == "sql":
    from .sql import SqlPixivRepo

    context.bind(LocalPixivRepo, SqlPixivRepo)
    logger.info(f"local cache: enabled ({conf.pixiv_sql_dialect})")
elif conf.pixiv_local_cache_type == "file":
    from .file import FilePixivRepo

    context.bind(LocalPixivRepo, FilePixivRepo)
    logger.info(f"local cache: enabled (file)")
else:
    raise RuntimeError(f"invalid pixiv_local_cache_type: {conf.pixiv_local_cache_type}")

__all__ = ("LocalPixivRepo",)
