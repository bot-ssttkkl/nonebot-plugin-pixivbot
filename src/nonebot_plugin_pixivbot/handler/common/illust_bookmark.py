from typing import Sequence

from nonebot import on_regex
from nonebot.internal.adapter import Event
from nonebot.internal.params import Depends
from nonebot.params import RegexGroup
from nonebot_plugin_session import extract_session

from .base import RecordCommonHandler
from ..pkg_context import context
from ..utils import get_common_query_rule
from ...config import Config
from ...plugin_service import illust_bookmark_add_service, illust_bookmark_delete_service
from ...service.pixiv_account_binder import PixivAccountBinder
from ...service.pixiv_service import PixivService
from ...utils.errors import BadRequestError

conf = context.require(Config)
binder = context.require(PixivAccountBinder)
service = context.require(PixivService)


class IllustBookmarkAddHandler(RecordCommonHandler, service=illust_bookmark_add_service):
    @classmethod
    def type(cls) -> str:
        return "illust_bookmark_add"

    @classmethod
    def enabled(cls) -> bool:
        return conf.pixiv_illust_bookmark_manage_enabled

    async def parse_args(self, args: Sequence[str]) -> dict:
        pixiv_user_id = 0

        if len(args) > 0:
            try:
                pixiv_user_id = int(args[0])
            except ValueError:
                raise BadRequestError(f"{args[0]}不是合法的ID")

        return {"pixiv_user_id": pixiv_user_id, "sender_user_id": self.session.id1}

    async def actual_handle(self, *, pixiv_user_id: int = 0,
                            sender_user_id: int = 0,
                            illust_id: int = 1):
        if not pixiv_user_id and sender_user_id:
            pixiv_user_id = await binder.get_binding(self.session.platform, sender_user_id)

        if not pixiv_user_id:
            pixiv_user_id = conf.pixiv_random_bookmark_user_id

        if not pixiv_user_id:
            raise BadRequestError("无效的Pixiv账号，或未绑定Pixiv账号")

        try:
            await service.illust_bookmark_add(illust_id)
            ok = True
        except:
            ok = False
            raise BadRequestError("收藏失败")
        finally:
            if ok:
                await self.post_plain_text("收藏成功")


@on_regex(r"^收藏\s*([1-9][0-9]*)$", rule=get_common_query_rule(), priority=5).handle()
async def _(event: Event,
            session=Depends(extract_session),
            matched_groups=RegexGroup()):
    illust_id = matched_groups[0]
    await IllustBookmarkAddHandler(session, event).handle(illust_id=illust_id)

class IllustBookmarkDeleteHandler(RecordCommonHandler, service=illust_bookmark_delete_service):
    @classmethod
    def type(cls) -> str:
        return "illust_bookmark_delete"

    @classmethod
    def enabled(cls) -> bool:
        return conf.pixiv_illust_bookmark_manage_enabled

    async def parse_args(self, args: Sequence[str]) -> dict:
        pixiv_user_id = 0

        if len(args) > 0:
            try:
                pixiv_user_id = int(args[0])
            except ValueError:
                raise BadRequestError(f"{args[0]}不是合法的ID")

        return {"pixiv_user_id": pixiv_user_id, "sender_user_id": self.session.id1}

    async def actual_handle(self, *, pixiv_user_id: int = 0,
                            sender_user_id: int = 0,
                            illust_id: int = 1):
        if not pixiv_user_id and sender_user_id:
            pixiv_user_id = await binder.get_binding(self.session.platform, sender_user_id)

        if not pixiv_user_id:
            pixiv_user_id = conf.pixiv_random_bookmark_user_id

        if not pixiv_user_id:
            raise BadRequestError("无效的Pixiv账号，或未绑定Pixiv账号")

        try:
            await service.illust_bookmark_delete(illust_id)
            ok = True
        except:
            ok = False
            raise BadRequestError("取消收藏失败")
        finally:
            if ok:
                await self.post_plain_text("取消收藏成功")


@on_regex(r"^取消收藏\s*([1-9][0-9]*)$", rule=get_common_query_rule(), priority=5).handle()
async def _(event: Event,
            session=Depends(extract_session),
            matched_groups=RegexGroup()):
    illust_id = matched_groups[0]
    await IllustBookmarkDeleteHandler(session, event).handle(illust_id=illust_id)
