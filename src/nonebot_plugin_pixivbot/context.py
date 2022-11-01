from abc import ABC, abstractmethod
from typing import TypeVar, Type, Callable, Union, Generic

from nonebot.log import logger

T = TypeVar("T")
T2 = TypeVar("T2")


class Inject:
    def __init__(self, key):
        self._key = key

    def __get__(self, instance, owner):
        context = getattr(instance, "__context__")
        return context.require(self._key)


class Provider(ABC, Generic[T]):
    @abstractmethod
    def provide(self) -> T:
        raise NotImplementedError()


class InstanceProvider(Provider[T], Generic[T]):
    def __init__(self, instance: T):
        self._instance = instance

    def provide(self) -> T:
        return self._instance


class DynamicProvider(Provider[T], Generic[T]):
    def __init__(self, func: Callable[[], T], use_cache: bool = True):
        self._func = func
        self._use_cache = use_cache

        self._cache = None
        self._cached = False

    def provide(self) -> T:
        if not self._use_cache:
            return self._func()

        if not self._cached:
            self._cache = self._func()  # just let it throw
            self._cached = True
        return self._cache


class Context:
    def __init__(self, parent: "Context" = None):
        self._parent = parent
        self._container = {}

    @property
    def parent(self) -> "Context":
        return self._parent

    @property
    def root(self) -> "Context":
        if self._parent is None:
            return self
        else:
            return self._parent.root

    def register(self, key: Type[T], bean: Union[T, Provider[T]]):
        """
        register a bean
        """
        if not isinstance(bean, Provider):
            bean = InstanceProvider(bean)

        self._container[key] = bean
        logger.trace(f"registered bean {key}, provider type: {type(bean)}")

    def register_lazy(self, key: Type[T], bean_initializer: Callable[[], T]):
        """
        register a bean lazily
        """
        self._container[key] = DynamicProvider(bean_initializer)
        logger.trace(f"lazily registered bean {key}")

    def register_singleton(self, *args, **kwargs) -> Callable[[Type[T]], Type[T]]:
        """
        decorator for a class to register a bean lazily
        """

        def decorator(cls: Type[T]) -> Type[T]:
            self.register_lazy(cls, lambda: cls(*args, **kwargs))
            return cls

        return decorator

    def register_eager_singleton(self, *args, **kwargs) -> Callable[[Type[T]], Type[T]]:
        """
        decorator for a class to register a bean lazily
        """

        def decorator(cls: Type[T]) -> Type[T]:
            bean = cls(*args, **kwargs)
            self.register(cls, bean)
            return cls

        return decorator

    def unregister(self, key: Type[T]) -> bool:
        """
        unregister the bean of key
        """
        if key in self._container:
            del self._container[key]
            return True
        return False

    def bind(self, key: Type[T], src_key: Type[T2]):
        """
        bind key (usually the implementation class) to src_key (usually the base class)
        """
        self._container[key] = self._find_provider(src_key)
        logger.trace(f"bind bean {key} to {src_key}")

    def bind_singleton_to(self, key: Type[T], *args, **kwargs) -> Callable[[Type[T2]], Type[T2]]:
        """
        decorator for a class (usually the implementation class) to bind to another class (usually the base class)
        """

        def decorator(cls: Type[T2]) -> Type[T2]:
            self.register_singleton(*args, **kwargs)(cls)
            self.bind(key, cls)
            return cls

        return decorator

    def require(self, key: Type[T]) -> T:
        return self._find_provider(key).provide()

    def _find_provider(self, key: Type[T]) -> T:
        if key in self._container:
            return self._container[key]
        elif self._parent is not None:
            return self._parent._find_provider(key)
        else:
            raise KeyError(key)

    def __getitem__(self, key: Type[T]):
        return self.require(key)

    def __contains__(self, key: Type[T]) -> bool:
        if key in self._container:
            return True
        elif self._parent is not None:
            return self._parent.__contains__(key)
        else:
            return False

    def inject(self, cls: Type[T]):
        setattr(cls, "__context__", self)
        return cls


__all__ = ("Context", "Inject")
