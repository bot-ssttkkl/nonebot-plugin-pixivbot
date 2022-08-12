class LazyDelegation:
    def __init__(self, builder):
        self.cache = None
        self.builder = builder

    def __getattribute__(self, item):
        if object.__getattribute__(self, "cache") is None:
            object.__setattr__(self, "cache", object.__getattribute__(self, "builder")())
        return getattr(object.__getattribute__(self, "cache"), item)
