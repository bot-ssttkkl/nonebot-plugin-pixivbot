from nonebot_plugin_pixivbot.context import Context
from nonebot_plugin_pixivbot.global_context import context as parent_context

context = Context(parent=parent_context)

__all__ = ("context",)
