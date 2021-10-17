from pydantic import BaseSettings


class Config(BaseSettings):
    pixiv_refresh_token: str
    pixiv_mongodb_name: str

    class Config:
        extra = "ignore"
