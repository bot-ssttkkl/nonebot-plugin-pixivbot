import asyncio
from asyncio import sleep, create_task, CancelledError, Semaphore, Task
from functools import wraps
from io import BytesIO
from typing import TypeVar, Optional, Awaitable, List, Callable, Union, Tuple, AsyncGenerator

from nonebot import logger
from pixivpy_async import *
from pixivpy_async.error import TokenError

from nonebot_plugin_pixivbot.config import Config
from nonebot_plugin_pixivbot.enums import DownloadQuantity, RankingMode
from nonebot_plugin_pixivbot.model import Illust, User
from nonebot_plugin_pixivbot.utils.errors import QueryError
from .abstract_repo import AbstractPixivRepo
from .compressor import Compressor
from .lazy_illust import LazyIllust
from .pkg_context import context
from ..local_tag_repo import LocalTagRepo
from ...utils.lifecycler import on_startup, on_shutdown


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


T = TypeVar("T")


@context.inject
@context.register_eager_singleton()
class RemotePixivRepo(AbstractPixivRepo):
    _conf: Config
    _local_tags: LocalTagRepo
    _compressor: Compressor

    def __init__(self):
        self._sema: Semaphore = None
        self._pclient: PixivClient = None
        self._papi: AppPixivAPI = None
        self._refresh_daemon_task: Task = None

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

    async def _refresh_daemon(self):
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
        self._refresh_daemon_task = create_task(self._refresh_daemon())
        self._sema = Semaphore(self._conf.pixiv_simultaneous_query)

    async def shutdown(self):
        await self._pclient.close()
        self._refresh_daemon_task.cancel()

    @staticmethod
    def _check_error_in_raw_result(raw_result: dict):
        if "error" in raw_result:
            raise QueryError(raw_result["error"]["user_message"]
                             or raw_result["error"]["message"] or raw_result["error"]["reason"])

    async def _load_page(self, papi_search_func: Callable[..., Awaitable[dict]],
                         element_list_name: str,
                         *, mapper: Optional[Callable[[dict], T]] = None,
                         filter: Optional[Callable[[T], bool]] = None,
                         skip: int = 0,
                         limit: int = 0,
                         limit_page: int = 0,
                         **kwargs) -> AsyncGenerator[List[T], None]:
        """
        一次加载多页
        :param papi_search_func: PixivPy-Async的加载方法
        :param element_list_name: 返回JSON中元素所在列表名
        :param mapper: 将元素从JSON格式映射为特定格式
        :param filter: 过滤不符合条件的元素（先映射再过滤）
        :param abort_on: 加载完一页后判断是否要中断
        :param skip: 跳过指定项数
        :param limit: 最多加载多少项
        :param limit_page: 最多加载多少页
        :param kwargs: 传给papi_search_func的参数
        :return: 加载结果
        """
        papi_search_func = auto_retry(papi_search_func)

        loaded_items = 0
        loaded_pages = 0

        if skip:
            raw_result = await papi_search_func(offset=skip, **kwargs)
        else:
            raw_result = await papi_search_func(**kwargs)
        self._check_error_in_raw_result(raw_result)

        while True:
            # 加载下一页
            pending = []
            for x in raw_result[element_list_name]:
                element = x
                if mapper is not None:
                    element = mapper(x)
                if filter is not None and not filter(element):
                    break
                pending.append(element)
                if loaded_items + len(pending) == limit:
                    break

            loaded_pages = loaded_pages + 1
            loaded_items += len(pending)
            logger.debug(f"[remote] {loaded_pages} pages loaded ({loaded_items} items in total)")
            yield pending

            # 判断是否中断
            if (0 < limit <= loaded_items) or \
                    (0 < limit_page <= loaded_pages):
                break
            else:
                next_qs = AppPixivAPI.parse_qs(next_url=raw_result["next_url"])
                if next_qs is None:
                    break

                if 'viewed' in next_qs:
                    # 由于pixivpy-async的illust_recommended的bug，需要删掉这个参数
                    del next_qs['viewed']

                raw_result = await papi_search_func(**next_qs)
                self._check_error_in_raw_result(raw_result)

    async def _add_to_local_tags(self, illusts: List[Union[LazyIllust, Illust]]):
        try:
            tags = {}
            for x in illusts:
                if isinstance(x, LazyIllust):
                    if not x.loaded:
                        continue
                    x = x.content
                for t in x.tags:
                    if t.translated_name:
                        tags[t.name] = t

            await self._local_tags.insert_many(tags.values())
        except Exception as e:
            logger.exception(e)

    async def _get_illusts(self, papi_search_func: Callable[[], Awaitable[dict]],
                           *, block_tags: Optional[List[str]] = None,
                           min_bookmark: int = 0,
                           min_view: int = 0,
                           skip: int = 0,
                           limit: int = 0,
                           limit_page: int = 0,
                           **kwargs) -> AsyncGenerator[LazyIllust, None]:
        """
        加载插画
        :param papi_search_func: PixivPy-Async的加载方法
        :param block_tags: 要过滤的标签
        :param min_bookmark: 书签数下限
        :param min_view: 阅读数下限
        :param abort_on: 加载完一页后判断是否要中断
        :param skip: 跳过指定项数
        :param limit: 最多加载多少项
        :param limit_page: 最多加载多少页
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

        await self._sema.acquire()
        try:
            async for page in self._load_page(papi_search_func, "illusts",
                                              mapper=lambda x: Illust.parse_obj(x),
                                              filter=illust_filter,
                                              skip=skip,
                                              limit=limit,
                                              limit_page=limit_page,
                                              **kwargs):
                if self._conf.pixiv_tag_translation_enabled:
                    create_task(self._add_to_local_tags(page))

                for item in page:
                    total += 1
                    if "limit_unknown_360.png" in item.image_urls.large:
                        broken += 1
                        yield LazyIllust(item.id)
                    else:
                        yield LazyIllust(item.id, item)
        finally:
            self._sema.release()
            logger.debug(f"[remote] {total} got, illust_detail of {broken} are missed")

    @auto_retry
    async def illust_detail(self, illust_id: int) -> Illust:
        logger.debug(f"[remote] illust_detail {illust_id}")

        await self._sema.acquire()
        try:
            raw_result = await self._papi.illust_detail(illust_id)
            self._check_error_in_raw_result(raw_result)
            illust = Illust.parse_obj(raw_result["illust"])

            if self._conf.pixiv_tag_translation_enabled:
                create_task(self._add_to_local_tags([illust]))

            return illust
        finally:
            self._sema.release()

    @auto_retry
    async def user_detail(self, user_id: int) -> User:
        logger.debug(f"[remote] user_detail {user_id}")

        await self._sema.acquire()
        try:
            raw_result = await self._papi.user_detail(user_id)
            self._check_error_in_raw_result(raw_result)
            return User.parse_obj(raw_result["user"])
        finally:
            self._sema.release()

    async def search_illust(self, word: str) -> AsyncGenerator[LazyIllust, None]:
        logger.debug(f"[remote] search_illust {word}")
        async for x in self._get_illusts(self._papi.search_illust,
                                         block_tags=self._conf.pixiv_block_tags,
                                         min_bookmark=self._conf.pixiv_random_illust_min_bookmark,
                                         min_view=self._conf.pixiv_random_illust_min_view,
                                         limit=self._conf.pixiv_random_illust_max_item,
                                         limit_page=self._conf.pixiv_random_illust_max_page,
                                         word=word):
            yield x

    async def search_user(self, word: str) -> AsyncGenerator[User, None]:
        logger.debug(f"[remote] search_user {word}")
        async for page in self._load_page(self._papi.search_user, "user_previews",
                                          mapper=lambda x: User.parse_obj(x["user"]),
                                          limit_page=1,
                                          word=word):
            for item in page:
                yield item

    async def user_illusts(self, user_id: int) -> AsyncGenerator[LazyIllust, None]:
        logger.debug(f"[remote] user_illusts {user_id}")
        async for x in self._get_illusts(self._papi.user_illusts,
                                         block_tags=self._conf.pixiv_block_tags,
                                         min_bookmark=self._conf.pixiv_random_user_illust_min_bookmark,
                                         min_view=self._conf.pixiv_random_user_illust_min_view,
                                         limit=self._conf.pixiv_random_user_illust_max_item,
                                         limit_page=self._conf.pixiv_random_user_illust_max_page,
                                         user_id=user_id):
            yield x

    async def user_bookmarks(self, user_id: int = 0) -> AsyncGenerator[LazyIllust, None]:
        if user_id == 0:
            user_id = self.user_id

        logger.debug(f"[remote] user_bookmarks {user_id}")
        async for x in self._get_illusts(self._papi.user_bookmarks_illust,
                                         block_tags=self._conf.pixiv_block_tags,
                                         min_bookmark=self._conf.pixiv_random_bookmark_min_bookmark,
                                         min_view=self._conf.pixiv_random_bookmark_min_view,
                                         limit=self._conf.pixiv_random_bookmark_max_item,
                                         limit_page=self._conf.pixiv_random_bookmark_max_page,
                                         user_id=user_id):
            yield x

    async def recommended_illusts(self) -> AsyncGenerator[LazyIllust, None]:
        logger.debug(f"[remote] recommended_illusts")
        async for x in self._get_illusts(self._papi.illust_recommended,
                                         block_tags=self._conf.pixiv_block_tags,
                                         min_bookmark=self._conf.pixiv_random_recommended_illust_min_bookmark,
                                         min_view=self._conf.pixiv_random_recommended_illust_min_view,
                                         limit=self._conf.pixiv_random_recommended_illust_max_item,
                                         limit_page=self._conf.pixiv_random_recommended_illust_max_page):
            yield x

    async def related_illusts(self, illust_id: int) -> AsyncGenerator[LazyIllust, None]:
        logger.debug(f"[remote] related_illusts {illust_id}")
        async for x in self._get_illusts(self._papi.illust_related,
                                         block_tags=self._conf.pixiv_block_tags,
                                         min_bookmark=self._conf.pixiv_random_related_illust_min_bookmark,
                                         min_view=self._conf.pixiv_random_related_illust_min_view,
                                         limit=self._conf.pixiv_random_related_illust_max_item,
                                         limit_page=self._conf.pixiv_random_related_illust_max_page,
                                         illust_id=illust_id):
            yield x

    async def illust_ranking(self, mode: RankingMode, range: Tuple[int, int]) -> List[LazyIllust]:
        logger.debug(f"[repo] illust_ranking {mode} {range[0]}~{range[1]}")
        return [x async for x in self._get_illusts(self._papi.illust_ranking,
                                                   block_tags=self._conf.pixiv_block_tags,
                                                   skip=range[0] - 1,
                                                   limit=range[1] - range[0] + 1,
                                                   mode=mode.name)]

    @auto_retry
    async def image(self, illust: Illust) -> bytes:
        logger.debug(f"[remote] image {illust.id}")

        await self._sema.acquire()
        try:
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
                await self._papi.download(url, fname=bio)
                content = bio.getvalue()
                content = await self._compressor.compress(content)
                return content
        finally:
            self._sema.release()
