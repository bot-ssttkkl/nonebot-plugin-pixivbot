from typing import Optional, Sequence

import pytest
from tzlocal import get_localzone

from tests import MyTest


class MockMessageModelMixin(MyTest):
    @pytest.fixture(autouse=True)
    def mock_illust_message_model(self, load_pixivbot, monkeypatch):
        from nonebot_plugin_pixivbot.model import Illust
        from nonebot_plugin_pixivbot.model.message import IllustMessageModel

        async def mock_from_illust(illust: Illust, *,
                             header: Optional[str] = None,
                             number: Optional[int] = None):
            return IllustMessageModel(
                id=illust.id,
                header=header,
                number=number,
                image=bytes(),
                title=illust.title,
                author=f"{illust.user.name} ({illust.user.id})",
                create_time=illust.create_date.astimezone(get_localzone()).strftime('%Y-%m-%d %H:%M:%S'),
                link=f"https://www.pixiv.net/artworks/{illust.id}"
            )

        monkeypatch.setattr(IllustMessageModel, "from_illust", mock_from_illust)
        return mock_from_illust
