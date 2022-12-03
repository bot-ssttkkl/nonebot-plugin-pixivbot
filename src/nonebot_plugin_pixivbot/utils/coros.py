from functools import wraps
from inspect import isawaitable


def as_async(f):
    @wraps(f)
    async def wrapper(*args, **kwargs):
        x = f(*args, **kwargs)
        if isawaitable(x):
            x = await x
        return x

    return wrapper
