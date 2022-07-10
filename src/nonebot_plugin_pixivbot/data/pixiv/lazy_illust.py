import typing

from nonebot_plugin_pixivbot.model import Illust
from .pkg_context import context


class LazyIllust:
    src: 'PixivDataSource' = None

    @classmethod
    def init_src(cls):
        # 为避免循环引用，将import推迟到get的时候
        from .repo import PixivRepo
        cls.src = context.require(PixivRepo)

    def __init__(self, id: int, content: typing.Optional[Illust] = None) -> None:
        self.id = id
        self.content = content

    async def get(self):
        if self.content is None:
            if self.src is None:
                self.init_src()
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
