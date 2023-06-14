from functools import partial
from typing import Callable, Type, Optional, Iterable, TYPE_CHECKING

from .base import Interceptor

if TYPE_CHECKING:
    from ..base import Handler


class CombinedInterceptor(Interceptor):
    def __init__(self, x: Interceptor, y: Interceptor):
        self.x = x
        self.y = y

    @staticmethod
    def from_iterable(interceptors: Iterable[Interceptor]) -> "Interceptor":
        itcp = None
        for x in interceptors:
            if itcp is None:
                itcp = x
            else:
                itcp = CombinedInterceptor(itcp, x)
        if itcp is None:
            raise ValueError("interceptors has no element")
        return itcp

    def flat(self) -> Iterable["Interceptor"]:
        if isinstance(self.x, CombinedInterceptor):
            yield from self.x.flat()
        else:
            yield self.x

        if isinstance(self.y, CombinedInterceptor):
            yield from self.y.flat()
        else:
            yield self.y

    def find(self, interceptor_type: Type[Interceptor]) -> Optional[Interceptor]:
        if isinstance(interceptor_type, CombinedInterceptor):
            raise ValueError("you are attempting to find a CombinedInterceptor")
        if isinstance(self.x, interceptor_type):
            return self.x
        elif isinstance(self.y, interceptor_type):
            return self.y
        else:
            result = None
            if isinstance(self.x, CombinedInterceptor):
                result = self.x.find(interceptor_type)
            if not result and isinstance(self.y, CombinedInterceptor):
                result = self.y.find(interceptor_type)
            return result

    async def intercept(self, handler: "Handler", wrapped_func: Callable, *args, **kwargs):
        await self.x.intercept(
            handler,
            partial(self.y.intercept, handler, wrapped_func),
            *args, **kwargs
        )
