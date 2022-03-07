import typing
from .Illust import Illust


class LazyIllust:
    id: int
    content: Illust

    def __init__(self, id: int, content: typing.Optional[Illust] = None) -> None:
        self.id = id
        self.content = content

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


    @classmethod
    def set_data_source(cls, src):
        cls.src = src