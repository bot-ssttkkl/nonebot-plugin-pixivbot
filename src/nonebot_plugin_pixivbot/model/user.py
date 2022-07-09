from pydantic import BaseModel


class User(BaseModel):
    id: int
    name: str
    account: str


__all__ = ("User",)
