from . import nb_providers
from .context import Context


def provide(context: Context):
    nb_providers.provide(context)
