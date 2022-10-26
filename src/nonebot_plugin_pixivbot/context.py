import functools
import inspect
import sys
import types
from threading import Lock
from typing import TypeVar, Type, Callable, Dict, Any

from nonebot.log import logger


# copied from inspect.py (py3.10)
def get_annotations(obj, *, globals=None, locals=None, eval_str=False) -> Dict[str, Any]:
    if sys.version_info >= (3, 10):
        return inspect.get_annotations(obj, globals=globals, locals=locals, eval_str=eval_str)

    if isinstance(obj, type):
        # class
        obj_dict = getattr(obj, '__dict__', None)
        if obj_dict and hasattr(obj_dict, 'get'):
            ann = obj_dict.get('__annotations__', None)
            if isinstance(ann, types.GetSetDescriptorType):
                ann = None
        else:
            ann = None

        obj_globals = None
        module_name = getattr(obj, '__module__', None)
        if module_name:
            module = sys.modules.get(module_name, None)
            if module:
                obj_globals = getattr(module, '__dict__', None)
        obj_locals = dict(vars(obj))
        unwrap = obj
    elif isinstance(obj, types.ModuleType):
        # module
        ann = getattr(obj, '__annotations__', None)
        obj_globals = getattr(obj, '__dict__')
        obj_locals = None
        unwrap = None
    elif callable(obj):
        # this includes types.Function, types.BuiltinFunctionType,
        # types.BuiltinMethodType, functools.partial, functools.singledispatch,
        # "class funclike" from Lib/test/test_inspect... on and on it goes.
        ann = getattr(obj, '__annotations__', None)
        obj_globals = getattr(obj, '__globals__', None)
        obj_locals = None
        unwrap = obj
    else:
        raise TypeError(f"{obj!r} is not a module, class, or callable.")

    if ann is None:
        return {}

    if not isinstance(ann, dict):
        raise ValueError(f"{obj!r}.__annotations__ is neither a dict nor None")

    if not ann:
        return {}

    if not eval_str:
        return dict(ann)

    if unwrap is not None:
        while True:
            if hasattr(unwrap, '__wrapped__'):
                unwrap = unwrap.__wrapped__
                continue
            if isinstance(unwrap, functools.partial):
                unwrap = unwrap.func
                continue
            break
        if hasattr(unwrap, "__globals__"):
            obj_globals = unwrap.__globals__

    if globals is None:
        globals = obj_globals
    if locals is None:
        locals = obj_locals

    return_value = {key: value if not isinstance(value, str) else eval(value, globals, locals)
                    for key, value in ann.items()}
    return return_value


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
        logger.trace(f"registered bean {key}")

    def register_lazy(self, key: Type[T], bean_initializer: Callable[[], T]):
        """
        register a bean lazily
        """
        if key in self._container:
            del self._container[key]
        self._lazy_container[key] = bean_initializer
        logger.trace(f"lazily registered bean {key}")

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
        logger.trace(f"bind bean {key} to {src_key}")

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
            return self._parent.__contains__(key)
        else:
            return False

    def inject(self, cls: Type[T]):
        old_getattr = getattr(cls, "__getattr__", None)

        def __getattr__(obj: T, name: str):
            ann = get_annotations(cls, eval_str=True)
            if name in ann and ann[name] in self:
                return self[ann[name]]

            if old_getattr:
                return old_getattr(obj, name)
            else:
                for c in cls.mro()[1:]:
                    c_getattr = getattr(c, "__getattr__", None)
                    if c_getattr:
                        return c_getattr(obj, name)

        setattr(cls, "__getattr__", __getattr__)
        return cls


__all__ = ("Context",)
