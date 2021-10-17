from pydantic import *


class PixivError(BaseModel):
    user_message: str
    message: str
    reason: str
    user_message_details: dict
