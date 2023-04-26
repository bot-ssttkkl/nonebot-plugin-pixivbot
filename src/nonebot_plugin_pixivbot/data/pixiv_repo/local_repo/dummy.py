from nonebot_plugin_pixivbot.data.pixiv_repo.errors import NoSuchItemError
from nonebot_plugin_pixivbot.data.pixiv_repo.local_repo import LocalPixivRepo

from nonebot_plugin_pixivbot.global_context import context


@context.register_singleton()
class DummyPixivRepo(LocalPixivRepo):
    # ================ illust_detail ================
    async def illust_detail(self, *args, **kwargs):
        raise NoSuchItemError()
        yield None

    async def update_illust_detail(self, *args, **kwargs):
        pass

    # ================ user_detail ================
    async def user_detail(self, *args, **kwargs):
        raise NoSuchItemError()
        yield None

    async def update_user_detail(self, *args, **kwargs):
        pass

    # ================ search_illust ================
    async def search_illust(self, *args, **kwargs):
        raise NoSuchItemError()
        yield None

    async def invalidate_search_illust(self, *args, **kwargs):
        pass

    async def append_search_illust(self, *args, **kwargs) -> bool:
        return False

    # ================ search_user ================
    async def search_user(self, *args, **kwargs):
        raise NoSuchItemError()
        yield None

    async def invalidate_search_user(self, *args, **kwargs):
        pass

    async def append_search_user(self, *args, **kwargs) -> bool:
        return False

    # ================ user_illusts ================
    async def user_illusts(self, *args, **kwargs):
        raise NoSuchItemError()
        yield None

    async def invalidate_user_illusts(self, *args, **kwargs):
        pass

    async def append_user_illusts(self, *args, **kwargs) -> bool:
        return False

    # ================ user_bookmarks ================
    async def user_bookmarks(self, *args, **kwargs):
        raise NoSuchItemError()
        yield None

    async def invalidate_user_bookmarks(self, *args, **kwargs):
        pass

    async def append_user_bookmarks(self, *args, **kwargs) -> bool:
        return False

    # ================ recommended_illusts ================
    async def recommended_illusts(self, *args, **kwargs):
        raise NoSuchItemError()
        yield None

    async def invalidate_recommended_illusts(self, *args, **kwargs):
        pass

    async def append_recommended_illusts(self, *args, **kwargs) -> bool:
        return False

    # ================ related_illusts ================
    async def related_illusts(self, *args, **kwargs):
        raise NoSuchItemError()
        yield None

    async def invalidate_related_illusts(self, *args, **kwargs):
        pass

    async def append_related_illusts(self, *args, **kwargs) -> bool:
        return False

    # ================ illust_ranking ================
    async def illust_ranking(self, *args, **kwargs):
        raise NoSuchItemError()
        yield None

    async def invalidate_illust_ranking(self, *args, **kwargs):
        pass

    async def append_illust_ranking(self, *args, **kwargs) -> bool:
        return False

    # ================ image ================
    async def image(self, *args, **kwargs):
        raise NoSuchItemError()
        yield None

    async def update_image(self, *args, **kwargs):
        pass

    async def invalidate_all(self, *args, **kwargs):
        pass
