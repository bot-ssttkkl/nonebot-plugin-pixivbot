from .Illust import Illust


class LazyIllust:
    def __init__(self, illust_id, data_src, content=None):
        self.id = illust_id
        self.data_src = data_src
        self.content = content

    async def get(self, local=False) -> Illust:
        if self.content is None:
            if local:
                self.content = await self.data_src.illust_detail_local(self.id)
            else:
                self.content = await self.data_src.illust_detail(self.id)
        return self.content


__all__ = ("LazyIllust", )
