from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel, Field


class PixivRepoMetadata(BaseModel):
    update_time: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    pages: Optional[int]
    next_qs: Optional[dict]


__all__ = ("PixivRepoMetadata",)
