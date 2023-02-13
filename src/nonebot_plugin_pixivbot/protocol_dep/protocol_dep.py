from abc import ABC, ABCMeta
from typing import Dict, TypeVar, Generic, Type

from nonebot_plugin_pixivbot.global_context import context

T = TypeVar("T", bound="ProtocolDep", covariant=True)


class ProtocolDepManager(Generic[T], ABC):
    factories: Dict[str, Type[T]] = {}

    @classmethod
    def register(cls, type: Type[T]) -> Type[T]:
        cls.factories[type.adapter] = type
        if type not in context:
            context.register_singleton()(type)
        return type

    def require(self, adapter: str):
        t = self.factories.get(adapter, None)
        if t is None:
            raise RuntimeError(f"暂不支持{adapter}")
        return context.require(t)

    def __getitem__(self, adapter: str):
        return self.require(adapter)


class ProtocolDepMeta(ABCMeta):
    def __new__(mcs, *args, **kwargs):
        manager = None
        if 'manager' in kwargs:
            manager = kwargs['manager']
            del kwargs['manager']
        cls = super().__new__(mcs, *args, **kwargs)
        if manager:
            manager.register(cls)
        return cls


class ProtocolDep(metaclass=ProtocolDepMeta):
    adapter: str


__all__ = ("ProtocolDep", "ProtocolDepManager")
