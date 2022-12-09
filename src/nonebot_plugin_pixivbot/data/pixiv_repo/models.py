from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel, Field


class PixivRepoMetadata(BaseModel):
    update_time: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    pages: Optional[int]
    next_qs: Optional[dict]

    def __str__(self):
        return '(' + ', '.join(map(lambda kv: kv[0] + '=' + str(kv[1]), self.dict(exclude_none=True).items())) + ')'


__all__ = ("PixivRepoMetadata",)
