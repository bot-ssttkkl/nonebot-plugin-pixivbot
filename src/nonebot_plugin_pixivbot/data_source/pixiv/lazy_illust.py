import typing
from ...model import Illust
from .pkg_context import context

_src = None


def init_src():
    global _src
    # 为避免循环引用，将import推迟到get的时候
    from .pixiv_data_source import PixivDataSource
    _src = context.require(PixivDataSource)


class LazyIllust:
    def __init__(self, id: int, content: typing.Optional[Illust] = None) -> None:
        self.id = id
        self.content = content

    async def get(self):
        if self.content is None:
            if _src is None:
                init_src()
            self.content = await _src.illust_detail(self.id)
        return self.content

    @property
    def loaded(self):
        return self.content is not None

    def __getattr__(self, attr):
        if self.content is None:
            return None
        else:
            return self.content.__getattribute__(attr)
