from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from nonebot_plugin_pixivbot.data.pixiv_repo.abstract_repo import PixivRepoMetadata


class DataSourceNotReadyError(RuntimeError):
    pass

