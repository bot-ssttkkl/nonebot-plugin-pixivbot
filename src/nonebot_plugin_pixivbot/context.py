from threading import Lock
from typing import TypeVar, Type, Callable

from nonebot.log import logger

T = TypeVar("T")


class Context:
    def __init__(self, parent=None):
        self._parent = parent
        self._container = {}
        self._lazy_container = {}
        self._binding = {}
        self._lock = Lock()

    @property
    def parent(self):
        return self._parent

    @property
    def root(self):
        if self._parent is None:
            return self
        else:
            return self._parent.root

    def register(self, key: Type[T], bean: T):
        """
        register a bean
        """
        self._container[key] = bean
        logger.success(f"registered bean {key}")

    def register_lazy(self, key: Type[T], bean_initializer: Callable[[], T]):
        """
        register a bean lazily
        """
        if key in self._container:
            del self._container[key]
        self._lazy_container[key] = bean_initializer
        logger.success(f"lazily registered bean {key}")

    def register_singleton(self, *args, **kwargs):
        """
        decorator for a class to register a bean lazily
        """

        def decorator(cls):
            self.register_lazy(cls, lambda: cls(*args, **kwargs))
            return cls

        return decorator

    def register_eager_singleton(self, *args, **kwargs):
        """
        decorator for a class to register a bean lazily
        """

        def decorator(cls):
            bean = cls(*args, **kwargs)
            self.register(cls, bean)
            return cls

        return decorator

    def unregister(self, key: Type[T]):
        """
        unregister the bean of key
        """
        if key in self._container:
            del self._container[key]
        if key in self._lazy_container:
            del self._container[key]

    def bind_to(self, key, src_key):
        """
        bind key (usually the implementation class) to src_key (usually the base class)
        """
        self._binding[key] = src_key
        logger.success(f"bind bean {key} to {src_key}")

    def bind_singleton_to(self, key, *args, **kwargs):
        """
        decorator for a class (usually the implementation class) to bind to another class (usually the base class)
        """

        def decorator(cls):
            self.register_singleton(*args, **kwargs)(cls)
            self.bind_to(key, cls)
            return cls

        return decorator

    def require(self, key: Type[T]) -> T:
        if key in self._binding:
            return self.require(self._binding[key])
        elif key in self._container:
            return self._container[key]
        elif key in self._lazy_container:
            # TODO: Lock
            self.register(key, self._lazy_container[key]())
            del self._lazy_container[key]
            return self._container[key]
        elif self._parent is not None:
            return self._parent.require(key)
        else:
            raise KeyError(key)

    def __getitem__(self, key: Type[T]):
        return self.require(key)

    def __contains__(self, key: Type[T]) -> bool:
        if key in self._binding or key in self._container or key in self._lazy_container:
            return True
        elif self._parent is not None:
            return self._parent.contains(key)
        else:
            return False


__all__ = ("Context",)
