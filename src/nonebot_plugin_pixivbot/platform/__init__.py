from .available import register as register_available
from .func_manager import FuncManagerFactory

platform_func = FuncManagerFactory()
register_available(platform_func)

__all__ = ("platform_func",)
