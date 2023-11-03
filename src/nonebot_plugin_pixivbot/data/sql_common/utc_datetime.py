from datetime import datetime, timezone
from typing import Optional

import tzlocal
from sqlalchemy import TypeDecorator, DateTime, Dialect


class UTCDateTime(TypeDecorator):
    impl = DateTime
    LOCAL_TIMEZONE = tzlocal.get_localzone()
    cache_ok = True

    def process_bind_param(self, value: Optional[datetime], dialect: Dialect) -> Optional[datetime]:
        if value is None:
            return None

        if value.tzinfo is None:
            value = value.astimezone(self.LOCAL_TIMEZONE)

        return value.astimezone(timezone.utc).replace(tzinfo=None)

    def process_result_value(self, value: Optional[datetime], dialect: Dialect) -> Optional[datetime]:
        if value is None:
            return None

        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)

        return value.astimezone(timezone.utc)
