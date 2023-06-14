from functools import lru_cache
from typing import Callable, Mapping


class UnsupportedBotError(RuntimeError):
    ...


class FuncManager:
    def __init__(self, func: Mapping[str, Callable]):
        self._func = func

    def __getattr__(self, item):
        if item in self._func:
            return self._func[item]
        else:
            raise UnsupportedBotError()


class FuncManagerFactory:
    def __init__(self):
        self._registry = []

    def register(self, bot_type: str, func_name: str, func: Callable):
        self._registry.append((bot_type, func_name, func))

    @lru_cache(maxsize=8)
    def __call__(self, bot_type: str):
        func_mapping = {}
        for type_, name, func in self._registry:
            if bot_type == type_:
                func_mapping[name] = func
        return FuncManager(func_mapping)
