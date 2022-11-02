import typing

from pydantic import *


class Tag(BaseModel):
    name: str
    translated_name: typing.Optional[str] = None

    class Config:
        orm_mode = True


__all__ = ("Tag",)
