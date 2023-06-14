from nonebot_plugin_session import Session
from pydantic import BaseModel


class IntervalTask(BaseModel):
    code: str = ""
    subscriber: Session
