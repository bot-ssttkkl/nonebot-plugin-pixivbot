from pydantic import *


class Error(BaseModel):
    user_message: str
    message: str
    reason: str
    user_message_details: dict
