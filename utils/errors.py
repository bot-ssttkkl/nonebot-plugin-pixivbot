from pixivpy_async import PixivError


class QueryError(PixivError):
    def __init__(self, user_message, message, reason, user_message_details):
        self.reason = user_message or message or reason
        super(PixivError, self).__init__(self, self.reason)

    def __str__(self):
        return self.reason


class NoRetryError(Exception):
    def __init__(self, reason=""):
        self.reason = reason

    def __str__(self):
        return self.reason


__all__ = ("QueryError", "NoRetryError")
