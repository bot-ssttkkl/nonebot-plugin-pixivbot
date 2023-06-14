from pydantic import BaseModel


class PixivBinding(BaseModel):
    platform: str
    user_id: str
    pixiv_user_id: int
