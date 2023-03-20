from nonebot_plugin_pixivbot.data.pixiv_repo import PixivRepo
from nonebot_plugin_pixivbot.plugin_service import invalidate_cache_service
from .subcommand import SubCommandHandler
from ..interceptor.permission_interceptor import SuperuserInterceptor
from ..interceptor.service_interceptor import ServiceInterceptor
from ..pkg_context import context

repo = context.require(PixivRepo)


class InvalidateCacheHandler(SubCommandHandler, subcommand='invalidate_cache',
                             interceptors=[context.require(SuperuserInterceptor),
                                           ServiceInterceptor(invalidate_cache_service)]):

    @classmethod
    def type(cls) -> str:
        return "invalidate_cache"

    async def actual_handle(self):
        await repo.invalidate_cache()
        await self.post_plain_text(message="ok")
