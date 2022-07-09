class QueryError(Exception):
    def __init__(self, message):
        self.message = message

    def __str__(self):
        return self.message


class BadRequestError(Exception):
    def __init__(self, message=None):
        super().__init__()
        self.message = message

    def __str__(self):
        return self.message


__all__ = ("QueryError", "BadRequestError")
