from . import nb_provider
from .context import Context


def provide(context: Context):
    nb_provider.provide(context)
