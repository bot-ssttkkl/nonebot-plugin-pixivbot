from typing import TYPE_CHECKING

from nonebot_plugin_pixivbot.model import T_UID, T_GID
from nonebot_plugin_pixivbot.protocol_dep.post_dest import PostDestination
from .permission_interceptor import PermissionInterceptor

if TYPE_CHECKING:
    from nonebot_plugin_access_control.service import Service


class ServiceInterceptor(PermissionInterceptor):
    def __init__(self, service: "Service"):
        self.service = service

    async def has_permission(self, post_dest: PostDestination[T_UID, T_GID]) -> bool:
        subjects = post_dest.extract_subjects()
        return await self.service.get_permission(*subjects)
