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
        t = self.factories.get(adapter, None)
        if t is None:
            raise RuntimeError(f"未找到{adapter}协议的特化插件，请尝试安装nonebot-plugin-pixivbot[{adapter}]")
        return context.require(t)

    def __getitem__(self, adapter: str):
        return self.require(adapter)


__all__ = ("ProtocolDep", "ProtocolDepManager")
