from pydantic import *


class User(BaseModel):
    class ProfileImageUrls(BaseModel):
        medium: str

    id: int
    name: str
    account: str
    profile_image_urls: ProfileImageUrls
    is_followed: bool
