import typing

from pydantic import *


class Tag(BaseModel):
    name: str
    translated_name: typing.Optional[str] = None


__all__ = ("Tag",)
