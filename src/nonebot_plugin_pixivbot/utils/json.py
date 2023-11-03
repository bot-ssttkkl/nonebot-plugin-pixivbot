from datetime import datetime, date


def dumps_default(obj):
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()

    raise TypeError(f'Object of type {obj.__class__.__name__} '
                    f'is not JSON serializable')
