from . import apscheduler
from ..context import Context


def provide(context: Context):
    apscheduler.provide(context)


__all__ = ("provide",)
