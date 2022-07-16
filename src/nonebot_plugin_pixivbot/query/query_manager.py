from typing import Set, Type

from nonebot import logger, get_driver

from nonebot_plugin_pixivbot.global_context import context
from nonebot_plugin_pixivbot.query.query import Query


@context.register_singleton()
class QueryManager:
    def __init__(self):
        self.started = False
        self.t_queries: Set[Type[Query]] = set()

    def query(self, cls):
        if not self.started:
            self.t_queries.add(cls)
            logger.success(f"registered a query {cls}")
        else:
            query = cls()
            query.matcher.append_handler(query.on_match)
            logger.warning(f"registered a query {cls} after QueryManager started")
        return cls

    def start(self):
        if not self.started:
            for cls in self.t_queries:
                query = cls()
                query.matcher.append_handler(query.on_match)
            self.started = True

            logger.success("QueryManager Started.")


query_manager = context.require(QueryManager)
get_driver().on_startup(query_manager.start)
