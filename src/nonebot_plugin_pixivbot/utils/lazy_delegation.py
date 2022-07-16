from lazy import lazy


class LazyDelegation:
    def __init__(self, builder):
        self.builder = builder

    @lazy
    def by(self):
        return self.builder()

    def __getattr__(self, item):
        return self.by.__getattribute__(item)
