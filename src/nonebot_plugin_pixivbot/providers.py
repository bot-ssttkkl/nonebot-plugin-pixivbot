from .global_context import context
from .nb_provider import providers as nb_providers

providers = (*nb_providers,)

for p in providers:
    p(context)
