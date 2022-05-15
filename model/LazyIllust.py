import typing
from .Illust import Illust
from .pkg_context import context


class LazyIllust:
    def __init__(self, id: int, content: typing.Optional[Illust] = None) -> None:
        self.id = id
        self.content = content

    @property
    def src(self):
        # 为避免循环引用，将import推迟到get的时候
        from ..data_source import PixivDataSource
        return context.require(PixivDataSource)

    async def get(self):
        if self.content is None:
            self.content = await self.src.illust_detail(self.id)
        return self.content

    @property
    def loaded(self):
        return self.content is not None

    def __getattr__(self, attr):
        if self.content is None:
            return None
        else:
            return self.content.__getattribute__(attr)
