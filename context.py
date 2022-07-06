from threading import Lock
import typing

from nonebot.log import logger


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

    T = typing.TypeVar("T")

    def register(self, key: typing.Type[T], bean: T):
        """
        register a bean
        """
        self._container[key] = bean
        logger.info(f"registered a bean of type {key}")

    def register_lazy(self, key: typing.Type[T], bean_initializer: typing.Callable[[], T]):
        """
        register a bean lazily
        """
        if key in self._container:
            del self._container[key]
        self._lazy_container[key] = bean_initializer
        logger.info(f"lazily registered a bean of type {key}")

    def register_singleton(self, *args, **kwargs):
        """
        decorator for a class to register a bean lazily
        """
        def decorator(cls):
            self.register_lazy(cls, lambda: cls(*args, **kwargs))
            return cls
        return decorator

    def register_factory(self, key: typing.Type[T]):
        """
        decorator for a factory method to register a bean lazily
        """
        def decorator(func):
            self.register_lazy(key, func)
        return decorator

    def bind(self, key, src_key):
        self._binding[key] = src_key
        logger.info(f"bind bean type {key} to {src_key}")

    # def export(self, key: typing.Type[T], bean: T):
    #     self.root().register(key, bean)

    # def export_lazy(self, key: typing.Type[T], bean_initializer: typing.Callable[[], T]):
    #     self.root().register_lazy(key, bean_initializer)

    # def export_singleton(self, *args, **kwargs):
    #     def decorator(cls):
    #         self.export_lazy(cls, lambda: cls(*args, **kwargs))
    #         return cls
    #     return decorator

    def require(self, key: typing.Type[T]) -> T:
        if key in self._binding:
            return self.require(self._binding[key])
        elif key in self._container:
            return self._container[key]
        elif key in self._lazy_container:
            self._lock.acquire()
            try:
                if key in self._lazy_container:
                    self.register(key, self._lazy_container[key]())
                    del self._lazy_container[key]
            finally:
                self._lock.release()
            return self._container[key]
        elif self._parent is not None:
            return self._parent.require(key)
        else:
            raise KeyError(key)


__all__ = ("Context", )
