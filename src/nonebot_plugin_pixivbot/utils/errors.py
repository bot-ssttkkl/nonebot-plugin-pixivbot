from ssttkkl_nonebot_utils.errors.errors import QueryError as QE, BadRequestError as BRE

QueryError = QE
BadRequestError = BRE


class RateLimitError(QueryError):
    def __init__(self):
        super().__init__("Rate Limit")


class PostIllustError(QueryError):
    def __str__(self):
        super().__init__("发送图片失败")


__all__ = ("QueryError", "RateLimitError", "BadRequestError", "PostIllustError")
