from pydantic import BaseSettings


class Config(BaseSettings):
    pixiv_access_token: str
    pixiv_refresh_token: str

    class Config:
        extra = "ignore"