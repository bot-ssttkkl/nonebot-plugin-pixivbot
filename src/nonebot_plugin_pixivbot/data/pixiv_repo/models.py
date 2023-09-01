from datetime import datetime, timezone, timedelta
from typing import Optional

from pydantic import BaseModel, Field


class PixivRepoMetadata(BaseModel):
    update_time: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    pages: Optional[int]
    next_qs: Optional[dict]

    def check_is_expired(self, expires_in: int) -> "PixivRepoMetadata":
        if datetime.now(timezone.utc) - self.update_time >= timedelta(seconds=expires_in):
            from .errors import CacheExpiredError
            raise CacheExpiredError(self)
        return self


__all__ = ("PixivRepoMetadata",)
