from nonebot_plugin_pixivbot.model import WatchTask
from ..interval_task_repo import IntervalTaskRepo


class WatchTaskRepo(IntervalTaskRepo[WatchTask]):
    async def update(self, item: WatchTask) -> bool:
        ...
