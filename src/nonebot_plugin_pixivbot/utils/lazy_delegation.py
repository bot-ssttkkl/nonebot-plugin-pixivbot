class LazyDelegation:
    __slots__ = ("__cache__", "__builder__")

    def __init__(self, builder):
        object.__setattr__(self, "__cache__", None)
        object.__setattr__(self, "__builder__", builder)

    def __getattribute__(self, item):
        if object.__getattribute__(self, "__cache__") is None:
            object.__setattr__(self, "__cache__", object.__getattribute__(self, "__builder__")())
        return getattr(object.__getattribute__(self, "__cache__"), item)
