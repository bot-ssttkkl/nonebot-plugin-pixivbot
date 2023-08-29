from ssttkkl_nonebot_utils.errors.errors import QueryError as QE, BadRequestError as BRE

QueryError = QE
BadRequestError = BRE


class RateLimitError(QueryError):
    def __init__(self):
        super().__init__("Rate Limit")


__all__ = ("QueryError", "RateLimitError", "BadRequestError")
