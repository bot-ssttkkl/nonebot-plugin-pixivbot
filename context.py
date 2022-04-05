from xml.dom import NotFoundErr


class Context:
    def __init__(self, parent=None):
        self.parent = parent
        self.container = {}
        self.lazy_container = {}

    def register(self, key, bean):
        self.container[key] = bean

    def register_lazy(self, key, bean_initializer):
        if key in self.container:
            del self.container[key]
        self.lazy_container[key] = bean_initializer

    def _get_root(self):
        if self.parent is None:
            return self
        else:
            return self.parent._get_root()

    def export(self, key, bean):
        self._get_root().register(key, bean)

    def export_lazy(self, key, bean_initializer):
        self._get_root().register_lazy(key, bean_initializer)

    def require(self, key):
        if key in self.container:
            return self.container[key]
        elif key in self.lazy_container:
            self.register(key, self.lazy_container[key]())
            del self.lazy_container[key]
            return self.container[key]
        elif self.parent is not None:
            return self.parent.require(key)
        else:
            raise KeyError(key)

    def register_singleton(self, *args, **kwargs):
        def decorator(cls):
            self.register_lazy(cls, lambda: cls(*args, **kwargs))
            return cls
        return decorator

    def export_singleton(self, *args, **kwargs):
        def decorator(cls):
            self.export_lazy(cls, lambda: cls(*args, **kwargs))
            return cls
        return decorator


__all__ = ("Context", )
