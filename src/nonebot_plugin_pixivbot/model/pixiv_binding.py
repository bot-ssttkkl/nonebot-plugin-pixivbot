from typing import Generic, TypeVar

from pydantic.generics import GenericModel

UID = TypeVar("UID")


class PixivBinding(GenericModel, Generic[UID]):
    adapter: str
    user_id: UID
    pixiv_user_id: int
