from nonebot_plugin_pixivbot.data.pixiv_repo.models import PixivRepoMetadata


class LocalPixivRepoError(RuntimeError):
    pass


class NoSuchItemError(LocalPixivRepoError):
    pass


class CacheExpiredError(LocalPixivRepoError):
    def __init__(self, metadata: PixivRepoMetadata):
        self.metadata = metadata

