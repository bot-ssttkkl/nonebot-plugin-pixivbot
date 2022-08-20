from asyncio import sleep, create_task, CancelledError, Semaphore, Task
from functools import wraps
from io import BytesIO
from typing import TypeVar, Optional, Awaitable, List, Callable, Tuple, AsyncGenerator, Union

from nonebot import logger
from pixivpy_async import *
from pixivpy_async.error import TokenError

from nonebot_plugin_pixivbot.config import Config
from nonebot_plugin_pixivbot.data.local_tag_repo import LocalTagRepo
from nonebot_plugin_pixivbot.enums import DownloadQuantity, RankingMode
from nonebot_plugin_pixivbot.model import Illust, User, UserPreview
from nonebot_plugin_pixivbot.utils.errors import QueryError
from nonebot_plugin_pixivbot.utils.lifecycler import on_startup, on_shutdown
from .abstract_repo import AbstractPixivRepo, PixivRepoMetadata
from .compressor import Compressor
from .lazy_illust import LazyIllust
from .pkg_context import context

T = TypeVar("T")


def auto_retry(func):
    @wraps(func)
    async def wrapped(*args, **kwargs):
        err = None
        for t in range(10):
            try:
                return await func(*args, **kwargs)
            except CancelledError as e:
                raise e
            except Exception as e:
                logger.debug(f"Retrying... {t + 1}/10")
                logger.exception(e)
                err = e

        raise err

    return wrapped


def check_error_in_raw_result(raw_result: dict):
    if "error" in raw_result:
        raise QueryError(raw_result["error"]["user_message"]
                         or raw_result["error"]["message"] or raw_result["error"]["reason"])


@context.inject
@context.register_eager_singleton()
class RemotePixivRepo(AbstractPixivRepo):
    _conf: Config
    _local_tags: LocalTagRepo
    _compressor: Compressor

    # noinspection PyTypeChecker
    def __init__(self):
        self._sema: Semaphore = None
        self._pclient: PixivClient = None
        self._papi: AppPixivAPI = None
        self._refresh_daemon: Task = None

        self.user_id = 0

        on_startup(self.start, replay=True)
        on_shutdown(self.shutdown)

    async def _refresh(self):
        # Latest app version can be found using GET /old/application-info/android
        USER_AGENT = "PixivAndroidApp/5.0.234 (Android 11; Pixel 5)"
        # REDIRECT_URI = "https://app-api.pixiv.net/web/v1/users/auth/pixiv/callback"
        # LOGIN_URL = "https://app-api.pixiv.net/web/v1/login"
        AUTH_TOKEN_URL = "https://oauth.secure.pixiv.net/auth/token"
        CLIENT_ID = "MOBrBDS8blbauoSck0ZfDbtuzpyT"
        CLIENT_SECRET = "lsACyCD94FhDUtGTXi3QzcFE2uU1hqtDaKeqrdwj"

        refresh_token = self._conf.pixiv_refresh_token

        data = {
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "grant_type": "refresh_token",
            "include_policy": "true",
            "refresh_token": refresh_token,
        }
        result = await self._papi.requests_(method="POST", url=AUTH_TOKEN_URL, data=data,
                                            headers={"User-Agent": USER_AGENT},
                                            auth=False)
        if result.has_error:
            raise TokenError(None, result)
        else:
            self._papi.set_auth(result.access_token, result.refresh_token)
            self.user_id = result["user"]["id"]

            logger.success(
                f"refresh access token successfully. new token expires in {result.expires_in} seconds.")
            logger.debug(f"access_token: {result.access_token}")
            logger.debug(f"refresh_token: {result.refresh_token}")

            # maybe the refresh token will be changed (even thought i haven't seen it yet)
            if result.refresh_token != refresh_token:
                refresh_token = result.refresh_token
                logger.warning(
                    f"refresh token has been changed: {result.refresh_token}")

            return result

    async def _refresh_daemon_worker(self):
        while True:
            try:
                result = await self._refresh()
                await sleep(result.expires_in * 0.8)
            except CancelledError as e:
                raise e
            except Exception as e:
                logger.error(
                    "failed to refresh access token, will retry in 60s.")
                logger.exception(e)
                await sleep(60)

    def start(self):
        self._pclient = PixivClient(proxy=self._conf.pixiv_proxy)
        self._papi = AppPixivAPI(client=self._pclient.start())
        self._papi.set_additional_headers({'Accept-Language': 'zh-CN'})
        self._refresh_daemon = create_task(self._refresh_daemon_worker())
        self._sema = Semaphore(self._conf.pixiv_simultaneous_query)

    async def shutdown(self):
        await self._pclient.close()
        self._refresh_daemon.cancel()

    async def load_page(self, papi_search_func: Callable[..., Awaitable[dict]],
                        element_list_name: str,
                        *, mapper: Optional[Callable[[dict], T]] = None,
                        filter_item: Optional[Callable[[T], bool]] = None,
                        **kwargs) -> Tuple[List[T], PixivRepoMetadata]:
        """
        加载一页
        :param papi_search_func: PixivPy-Async的加载方法
        :param element_list_name: 返回JSON中元素所在列表名
        :param mapper: 将元素从JSON格式映射为特定格式
        :param filter_item: 过滤不符合条件的元素（先映射再过滤）
        :param kwargs: 传给papi_search_func的参数
        :return: 加载结果
        """
        papi_search_func = auto_retry(papi_search_func)

        async with self._sema:
            raw_result = await papi_search_func(**kwargs)

        check_error_in_raw_result(raw_result)

        pending = []
        for x in raw_result[element_list_name]:
            if mapper is not None:
                x = mapper(x)

            if not filter_item or filter_item(x):
                pending.append(x)

        metadata = PixivRepoMetadata(next_qs=AppPixivAPI.parse_qs(next_url=raw_result["next_url"]))

        return pending, metadata

    async def load_many_pages(self, papi_search_func: Callable[..., Awaitable[dict]],
                              element_list_name: str,
                              *, mapper: Optional[Callable[[dict], T]] = None,
                              filter_item: Optional[Callable[[T], bool]] = None,
                              **kwargs) -> AsyncGenerator[Tuple[List[T], PixivRepoMetadata], None]:
        """
        一次加载多页
        :param papi_search_func: PixivPy-Async的加载方法
        :param element_list_name: 返回JSON中元素所在列表名
        :param mapper: 将元素从JSON格式映射为特定格式
        :param filter_item: 过滤不符合条件的元素（先映射再过滤）
        :param kwargs: 传给papi_search_func的参数
        :return: 加载结果
        """
        loaded_items = 0
        loaded_pages = 0
        next_qs = kwargs

        while True:
            page, metadata = await self.load_page(papi_search_func, element_list_name,
                                                  mapper=mapper, filter_item=filter_item,
                                                  **next_qs)

            loaded_pages = loaded_pages + 1
            loaded_items += len(page)
            logger.debug(f"[remote] {loaded_pages} pages loaded ({loaded_items} items in total)")

            metadata.pages = loaded_pages
            yield page, metadata

            next_qs = metadata.next_qs
            if next_qs:
                if 'viewed' in next_qs:
                    # 由于pixivpy-async的illust_recommended的bug，需要删掉这个参数
                    del next_qs['viewed']
            else:
                break

    async def _get_illusts(self, papi_search_func: Callable[[], Awaitable[dict]],
                           *, block_tags: Optional[List[str]] = None,
                           min_bookmark: int = 0,
                           min_view: int = 0,
                           **kwargs) \
            -> AsyncGenerator[Union[LazyIllust, PixivRepoMetadata], None]:
        """
        加载插画
        :param papi_search_func: PixivPy-Async的加载方法
        :param block_tags: 要过滤的标签
        :param min_bookmark: 书签数下限
        :param min_view: 阅读数下限
        :param kwargs: 传给papi_search_func的参数
        :return:
        """

        def illust_filter(illust: Illust) -> bool:
            # 标签过滤
            if block_tags is not None:
                for tag in block_tags:
                    if illust.has_tag(tag):
                        return False
            # 书签下限过滤
            if illust.total_bookmarks < min_bookmark:
                return False
            # 浏览量下限过滤
            if illust.total_view < min_view:
                return False
            return True

        total = 0
        broken = 0

        yield PixivRepoMetadata(pages=0, next_qs=kwargs)
        async for page, metadata in self.load_many_pages(papi_search_func, "illusts",
                                                         mapper=lambda x: Illust.parse_obj(x),
                                                         filter_item=illust_filter,
                                                         **kwargs):
            for item in page:
                total += 1
                if "limit_unknown_360.png" in item.image_urls.large:
                    broken += 1
                    yield LazyIllust(item.id)
                else:
                    yield LazyIllust(item.id, item)
            yield metadata

    async def _get_user_previews(self, papi_search_func: Callable[[], Awaitable[dict]], **kwargs) \
            -> AsyncGenerator[Union[PixivRepoMetadata, UserPreview], None]:
        yield PixivRepoMetadata(pages=0, next_qs=kwargs)
        async with self._sema:
            async for page, metadata in self.load_many_pages(papi_search_func, "user_previews",
                                                             mapper=lambda x: UserPreview.parse_obj(x),
                                                             **kwargs):
                for item in page:
                    yield item
                yield metadata

    async def _get_users(self, papi_search_func: Callable[[], Awaitable[dict]], **kwargs) \
            -> AsyncGenerator[Union[PixivRepoMetadata, User], None]:
        yield PixivRepoMetadata(pages=0, next_qs=kwargs)
        async with self._sema:
            async for page, metadata in self.load_many_pages(papi_search_func, "user_previews",
                                                             mapper=lambda x: User.parse_obj(x["user"]),
                                                             **kwargs):
                for item in page:
                    yield item
                yield metadata

    @auto_retry
    async def _illust_detail(self, illust_id: int, **kwargs) -> Illust:
        logger.debug(f"[remote] illust_detail {illust_id}")
        async with self._sema:
            raw_result = await self._papi.illust_detail(illust_id, **kwargs)
            check_error_in_raw_result(raw_result)
            return Illust.parse_obj(raw_result["illust"])

    async def illust_detail(self, illust_id: int, **kwargs) -> AsyncGenerator[Illust, None]:
        data = await self._illust_detail(illust_id, **kwargs)
        yield PixivRepoMetadata()
        yield data

    @auto_retry
    async def _user_detail(self, user_id: int, **kwargs) -> User:
        logger.debug(f"[remote] user_detail {user_id}")
        async with self._sema:
            raw_result = await self._papi.user_detail(user_id, **kwargs)
            check_error_in_raw_result(raw_result)
            return User.parse_obj(raw_result["user"])

    async def user_detail(self, user_id: int, **kwargs) -> AsyncGenerator[User, None]:
        data = await self._user_detail(user_id, **kwargs)
        yield PixivRepoMetadata()
        yield data

    def search_illust(self, word: str, **kwargs) \
            -> AsyncGenerator[Union[LazyIllust, PixivRepoMetadata], None]:
        logger.debug(f"[remote] search_illust {word}")
        return self._get_illusts(self._papi.search_illust,
                                 block_tags=self._conf.pixiv_block_tags,
                                 min_bookmark=self._conf.pixiv_random_illust_min_bookmark,
                                 min_view=self._conf.pixiv_random_illust_min_view,
                                 word=word, **kwargs)

    def search_user(self, word: str, **kwargs) \
            -> AsyncGenerator[Union[User, PixivRepoMetadata], None]:
        logger.debug(f"[remote] search_user {word}")
        return self._get_users(self._papi.search_user,
                               word=word, **kwargs)

    def search_user_with_preview(self, word: str, **kwargs) \
            -> AsyncGenerator[Union[UserPreview, PixivRepoMetadata], None]:
        logger.debug(f"[remote] search_user {word}")
        return self._get_user_previews(self._papi.search_user,
                                       word=word, **kwargs)

    def user_following(self, user_id: int, **kwargs) \
            -> AsyncGenerator[Union[User, PixivRepoMetadata], None]:
        logger.debug(f"[remote] following_users {user_id}")
        return self._get_users(self._papi.user_following,
                               user_id=user_id, **kwargs)

    def user_following_with_preview(self, user_id: int, **kwargs) \
            -> AsyncGenerator[Union[UserPreview, PixivRepoMetadata], None]:
        logger.debug(f"[remote] following_users {user_id}")
        return self._get_user_previews(self._papi.user_following,
                                       user_id=user_id, **kwargs)

    def user_illusts(self, user_id: int, **kwargs) \
            -> AsyncGenerator[Union[LazyIllust, PixivRepoMetadata], None]:
        logger.debug(f"[remote] user_illusts {user_id}")
        return self._get_illusts(self._papi.user_illusts,
                                 block_tags=self._conf.pixiv_block_tags,
                                 min_bookmark=self._conf.pixiv_random_user_illust_min_bookmark,
                                 min_view=self._conf.pixiv_random_user_illust_min_view,
                                 user_id=user_id, **kwargs)

    def user_bookmarks(self, user_id: int = 0, **kwargs) \
            -> AsyncGenerator[Union[LazyIllust, PixivRepoMetadata], None]:
        if user_id == 0:
            user_id = self.user_id

        logger.debug(f"[remote] user_bookmarks {user_id}")
        return self._get_illusts(self._papi.user_bookmarks_illust,
                                 block_tags=self._conf.pixiv_block_tags,
                                 min_bookmark=self._conf.pixiv_random_bookmark_min_bookmark,
                                 min_view=self._conf.pixiv_random_bookmark_min_view,
                                 user_id=user_id, **kwargs)

    # def following_illusts(self, **kwargs) \
    #         -> AsyncGenerator[Union[LazyIllust, PixivRepoMetadata], None]:
    #     logger.debug(f"[remote] following_illusts")
    #     return self._get_illusts(self._papi.illust_follow,
    #                              block_tags=self._conf.pixiv_block_tags,
    #                              min_bookmark=self._conf.pixiv_random_following_illust_min_bookmark,
    #                              min_view=self._conf.pixiv_random_following_illust_min_view,
    #                              **kwargs)

    def recommended_illusts(self, **kwargs) \
            -> AsyncGenerator[Union[LazyIllust, PixivRepoMetadata], None]:
        logger.debug(f"[remote] recommended_illusts")
        return self._get_illusts(self._papi.illust_recommended,
                                 block_tags=self._conf.pixiv_block_tags,
                                 min_bookmark=self._conf.pixiv_random_recommended_illust_min_bookmark,
                                 min_view=self._conf.pixiv_random_recommended_illust_min_view,
                                 **kwargs)

    def related_illusts(self, illust_id: int, **kwargs) \
            -> AsyncGenerator[Union[LazyIllust, PixivRepoMetadata], None]:
        logger.debug(f"[remote] related_illusts {illust_id}")
        return self._get_illusts(self._papi.illust_related,
                                 block_tags=self._conf.pixiv_block_tags,
                                 min_bookmark=self._conf.pixiv_random_related_illust_min_bookmark,
                                 min_view=self._conf.pixiv_random_related_illust_min_view,
                                 illust_id=illust_id, **kwargs)

    def illust_ranking(self, mode: Union[str, RankingMode], **kwargs) \
            -> AsyncGenerator[Union[LazyIllust, PixivRepoMetadata], None]:
        if isinstance(mode, str):
            mode = RankingMode[mode]

        logger.debug(f"[repo] illust_ranking {mode}")
        return self._get_illusts(self._papi.illust_ranking,
                                 block_tags=self._conf.pixiv_block_tags,
                                 mode=mode.name, **kwargs)

    @auto_retry
    async def _image(self, illust: Illust, **kwargs) -> bytes:
        logger.debug(f"[remote] image {illust.id}")
        async with self._sema:
            download_quantity = self._conf.pixiv_download_quantity
            custom_domain = self._conf.pixiv_download_custom_domain

            if download_quantity == DownloadQuantity.original:
                if len(illust.meta_pages) > 0:
                    url = illust.meta_pages[0].image_urls.original
                else:
                    url = illust.meta_single_page.original_image_url
            else:
                url = getattr(illust.image_urls, download_quantity.name)

            if custom_domain is not None:
                url = url.replace("i.pximg.net", custom_domain)

            with BytesIO() as bio:
                await self._papi.download(url, fname=bio, **kwargs)
                content = bio.getvalue()
                content = await self._compressor.compress(content)
                return content

    async def image(self, illust: Illust, **kwargs) \
            -> AsyncGenerator[Union[bytes, PixivRepoMetadata], None]:
        data = await self._image(illust, **kwargs)
        yield PixivRepoMetadata()
        yield data


__all__ = ("RemotePixivRepo",)
