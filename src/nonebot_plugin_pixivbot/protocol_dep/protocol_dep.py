from abc import ABC, abstractmethod
from typing import Dict, TypeVar, Generic, Type

from nonebot_plugin_pixivbot.global_context import context


class ProtocolDep(ABC):
    @classmethod
    @abstractmethod
    def adapter(cls) -> str:
        raise NotImplementedError()


T = TypeVar("T", bound=ProtocolDep)


class ProtocolDepManager(Generic[T], ABC):
    def __init__(self):
        self.factories: Dict[str, Type[T]] = {}

    def register(self, cls: Type[T]):
        self.factories[cls.adapter()] = cls
        if cls not in context:
            context.register_singleton()(cls)
        return cls

    def require(self, adapter: str):
        return context.require(self.factories[adapter])

    def __getitem__(self, adapter: str):
        return self.require(adapter)


__all__ = ("ProtocolDep", "ProtocolDepManager")
