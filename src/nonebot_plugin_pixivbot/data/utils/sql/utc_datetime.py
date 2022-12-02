from datetime import datetime, timezone

import tzlocal
from sqlalchemy import TypeDecorator, DateTime


class UTCDateTime(TypeDecorator):
    impl = DateTime
    LOCAL_TIMEZONE = tzlocal.get_localzone()

    def process_bind_param(self, value: datetime, dialect):
        if value is None:
            return None

        if value.tzinfo is None:
            value = value.astimezone(self.LOCAL_TIMEZONE)

        return value.astimezone(timezone.utc).replace(tzinfo=None)

    def process_result_value(self, value, dialect):
        if value is None:
            return None

        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)

        return value.astimezone(timezone.utc)
