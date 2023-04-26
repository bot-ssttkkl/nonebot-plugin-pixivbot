def format_kwargs(**kwargs):
    return ', '.join(map(lambda k: f'{k}={kwargs[k]}', kwargs))
