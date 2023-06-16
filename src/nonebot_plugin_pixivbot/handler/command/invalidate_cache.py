from argparse import Namespace

from .command import SubCommandHandler
from ..interceptor.permission_interceptor import SuperuserInterceptor
from ..pkg_context import context
from ...data.pixiv_repo import PixivRepo
from ...plugin_service import invalidate_cache_service

repo = context.require(PixivRepo)


class InvalidateCacheHandler(SubCommandHandler, subcommand='invalidate_cache', service=invalidate_cache_service,
                             interceptors=[context.require(SuperuserInterceptor)]):

    @classmethod
    def type(cls) -> str:
        return "invalidate_cache"

    async def actual_handle(self, *, args: Namespace):
        await repo.invalidate_cache()
        await self.post_plain_text(message="ok")
