from ..context import Context
from ..global_context import context as parent_context

context = Context(parent=parent_context)

__all__ = ("context",)
