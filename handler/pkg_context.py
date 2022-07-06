from ..context import Context
from ..global_context import global_context as parent_context

context = Context(parent=parent_context)
