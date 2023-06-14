from abc import ABC, abstractmethod
from typing import Callable, TYPE_CHECKING

if TYPE_CHECKING:
    from ..base import Handler


class Interceptor(ABC):
    @abstractmethod
    async def intercept(self, handler: "Handler", wrapped_func: Callable, *args, **kwargs):
        raise NotImplementedError()


class DummyInterceptor(Interceptor):
    async def intercept(self, handler: "Handler", wrapped_func: Callable, *args, **kwargs):
        await wrapped_func(*args, **kwargs)
