from asyncio import sleep, create_task, CancelledError
from functools import wraps
from io import BytesIO
from sqlite3 import NotSupportedError
from typing import TypeVar, Optional, Awaitable, List, Any, Callable, Union

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
from .mediator import Mediator
from .pkg_context import context
from ..local_tag_repo import LocalTagRepo


def auto_retry(func):
    @wraps(func)
    async def wrapped(*args, **kwargs):
        err = None
        for t in range(10):
            try:
                return await func(*args, **kwargs)
            except QueryError as e:
                raise e
            except Exception as e:
                logger.info(f"Retrying... {t + 1}/10")
                logger.exception(e)
                err = e

        raise err

    return wrapped


T = TypeVar("T")


@context.register_singleton()
class RemotePixivRepo(AbstractPixivRepo):
    _conf: Config = context.require(Config)

    def __init__(self):
        self._local_tags = context.require(LocalTagRepo)
        self._compressor = context.require(Compressor)

        self._pclient = None
        self._papi = None
        self._refresh_daemon_task = None

        self.user_id = 0

        self.refresh_token = self._conf.pixiv_refresh_token
        self.simultaneous_query = self._conf.pixiv_simultaneous_query
        self.timeout = self._conf.pixiv_query_timeout
        self.proxy = self._conf.pixiv_proxy

        self._cache_manager = Mediator(
            simultaneous_query=self._conf.pixiv_simultaneous_query)

    async def _refresh(self):
        # Latest app version can be found using GET /old/application-info/android
        USER_AGENT = "PixivAndroidApp/5.0.234 (Android 11; Pixel 5)"
        # REDIRECT_URI = "https://app-api.pixiv.net/web/v1/users/auth/pixiv/callback"
        # LOGIN_URL = "https://app-api.pixiv.net/web/v1/login"
        AUTH_TOKEN_URL = "https://oauth.secure.pixiv.net/auth/token"
        CLIENT_ID = "MOBrBDS8blbauoSck0ZfDbtuzpyT"
        CLIENT_SECRET = "lsACyCD94FhDUtGTXi3QzcFE2uU1hqtDaKeqrdwj"

        data = {
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "grant_type": "refresh_token",
            "include_policy": "true",
            "refresh_token": self.refresh_token,
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
            logger.info(f"access_token: {result.access_token}")
            logger.info(f"refresh_token: {result.refresh_token}")

            # maybe the refresh token will be changed (even thought i haven't seen it yet)
            if result.refresh_token != self.refresh_token:
                self.refresh_token = result.refresh_token
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

    async def start(self):
        self._cache_manager = Mediator(self.simultaneous_query)
        self._pclient = PixivClient(proxy=self.proxy)
        self._papi = AppPixivAPI(client=self._pclient.start())
        self._papi.set_additional_headers({'Accept-Language': 'zh-CN'})
        self._refresh_daemon_task = create_task(self._refresh_daemon())

    async def shutdown(self):
        await self._pclient.close()
        self._refresh_daemon_task.cancel()

    @staticmethod
    def _check_error_in_raw_result(raw_result: dict):
        if "error" in raw_result:
            raise QueryError(raw_result["error"]["user_message"]
                             or raw_result["error"]["message"] or raw_result["error"]["reason"])

    async def _flat_page(self, papi_search_func: Callable[..., Awaitable[dict]],
                         element_list_name: str,
                         element_mapper: Optional[Callable[[Any], T]] = None,
                         element_filter: Optional[Callable[[T], bool]] = None,
                         skip: int = 0,
                         limit: int = 0,
                         limit_page: int = 0,
                         **kwargs) -> List[T]:
        cur_page = 0
        items = []

        # user_bookmarks_illust 没有offset参数
        if skip:
            raw_result = await papi_search_func(offset=skip, **kwargs)
        else:
            raw_result = await papi_search_func(**kwargs)

        self._check_error_in_raw_result(raw_result)

        while (not limit or len(items) < limit) and (not limit_page or cur_page < limit_page):
            for x in raw_result[element_list_name]:
                element = x
                if element_mapper is not None:
                    element = element_mapper(x)
                if element_filter is None or element_filter(element):
                    items.append(element)
                    if len(items) >= limit:
                        break
            else:
                next_qs = AppPixivAPI.parse_qs(next_url=raw_result["next_url"])
                if next_qs is None:
                    break

                if 'viewed' in next_qs:
                    # 由于pixivpy-async的illust_recommended的bug，需要删掉这个参数
                    del next_qs['viewed']

                cur_page = cur_page + 1
                raw_result = await papi_search_func(**next_qs)
                self._check_error_in_raw_result(raw_result)

        return items

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
                           element_list_name: str,
                           block_tags: Optional[List[str]],
                           min_bookmark: int = 0,
                           min_view: int = 0,
                           skip: int = 0,
                           limit: int = 0,
                           limit_page: int = 0,
                           **kwargs):
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

        items = await self._flat_page(papi_search_func, element_list_name,
                                      lambda x: Illust.parse_obj(x),
                                      illust_filter, skip, limit, limit_page,
                                      **kwargs)

        illusts = []
        detail_missing = 0
        for x in items:
            if "limit_unknown_360.png" in x.image_urls.large:
                detail_missing += 1
                illusts.append(LazyIllust(x.id))
            else:
                illusts.append(LazyIllust(x.id, x))

        logger.info(
            f"[remote] {len(illusts)} got, illust_detail of {detail_missing} are missed")

        if self._conf.pixiv_tag_translation_enabled:
            create_task(self._add_to_local_tags(illusts))

        return illusts

    @auto_retry
    async def illust_detail(self, illust_id: int) -> Illust:
        logger.info(f"[remote] illust_detail {illust_id}")

        raw_result = await self._papi.illust_detail(illust_id)
        self._check_error_in_raw_result(raw_result)
        illust = Illust.parse_obj(raw_result["illust"])

        if self._conf.pixiv_tag_translation_enabled:
            create_task(self._add_to_local_tags([illust]))

        return illust

    @auto_retry
    async def user_detail(self, user_id: int) -> User:
        logger.info(f"[remote] user_detail {user_id}")

        raw_result = await self._papi.user_detail(user_id)
        self._check_error_in_raw_result(raw_result)
        return User.parse_obj(raw_result["user"])

    @auto_retry
    async def search_illust(self, word: str, *, skip: int = 0, limit: int = 0) -> List[LazyIllust]:
        if not limit:
            limit = self._conf.pixiv_random_illust_max_item
        limit_page = self._conf.pixiv_random_illust_max_page
        min_bookmark = self._conf.pixiv_random_illust_min_bookmark
        min_view = self._conf.pixiv_random_illust_min_view
        block_tags = self._conf.pixiv_block_tags

        logger.info(f"[remote] search_illust {word}")
        return await self._get_illusts(self._papi.search_illust, "illusts",
                                       block_tags, min_bookmark, min_view, skip, limit, limit_page,
                                       word=word)

    @auto_retry
    async def search_user(self, word: str, *, skip: int = 0, limit: int = 20) -> List[User]:
        logger.info(f"[remote] search_user {word}")
        content = await self._flat_page(self._papi.search_user, "user_previews",
                                        lambda x: User.parse_obj(
                                            x["user"]), None,
                                        skip, limit, 1,
                                        word=word)
        return content

    @auto_retry
    async def user_illusts(self, user_id: int = 0, *, skip: int = 0, limit: int = 0) -> List[LazyIllust]:
        if user_id == 0:
            user_id = self.user_id

        if not limit:
            limit = self._conf.pixiv_random_user_illust_max_item

        limit_page = self._conf.pixiv_random_user_illust_max_page
        min_bookmark = self._conf.pixiv_random_user_illust_min_bookmark
        min_view = self._conf.pixiv_random_user_illust_min_view
        block_tags = self._conf.pixiv_block_tags

        logger.info(f"[remote] user_illusts {user_id}")
        return await self._get_illusts(self._papi.user_illusts, "illusts",
                                       block_tags, min_bookmark, min_view, skip, limit, limit_page,
                                       user_id=user_id)

    @auto_retry
    async def user_bookmarks(self, user_id: int = 0, *, skip: int = 0, limit: int = 0) -> List[LazyIllust]:
        if user_id == 0:
            user_id = self.user_id

        if skip:
            raise NotSupportedError("Argument skip is not supported")

        if not limit:
            limit = self._conf.pixiv_random_bookmark_max_item

        limit_page = self._conf.pixiv_random_bookmark_max_page
        min_bookmark = self._conf.pixiv_random_bookmark_min_bookmark
        min_view = self._conf.pixiv_random_bookmark_min_view
        block_tags = self._conf.pixiv_block_tags

        logger.info(f"[remote] user_bookmarks {user_id}")
        return await self._get_illusts(self._papi.user_bookmarks_illust, "illusts",
                                       block_tags, min_bookmark, min_view, skip, limit, limit_page,
                                       user_id=user_id)

    @auto_retry
    async def recommended_illusts(self, *, skip: int = 0, limit: int = 0) -> List[LazyIllust]:
        if not limit:
            limit = self._conf.pixiv_random_recommended_illust_max_item

        limit_page = self._conf.pixiv_random_recommended_illust_max_page
        min_bookmark = self._conf.pixiv_random_recommended_illust_min_bookmark
        min_view = self._conf.pixiv_random_recommended_illust_min_view
        block_tags = self._conf.pixiv_block_tags

        logger.info(f"[remote] recommended_illusts")
        return await self._get_illusts(self._papi.illust_recommended, "illusts",
                                       block_tags, min_bookmark, min_view, skip, limit, limit_page)

    @auto_retry
    async def related_illusts(self, illust_id: int, *, skip: int = 0, limit: int = 0) -> List[LazyIllust]:
        if not limit:
            limit = self._conf.pixiv_random_related_illust_max_item

        limit_page = self._conf.pixiv_random_related_illust_max_page
        min_bookmark = self._conf.pixiv_random_related_illust_min_bookmark
        min_view = self._conf.pixiv_random_related_illust_min_view
        block_tags = self._conf.pixiv_block_tags

        logger.info(f"[remote] related_illusts {illust_id}")
        return await self._get_illusts(self._papi.illust_related, "illusts",
                                       block_tags, min_bookmark, min_view, skip, limit, limit_page,
                                       illust_id=illust_id)

    @auto_retry
    async def illust_ranking(self, mode: RankingMode = RankingMode.day,
                             *, skip: int = 0, limit: int = 0) -> List[LazyIllust]:
        if not limit:
            limit = self._conf.pixiv_ranking_fetch_item

        block_tags = self._conf.pixiv_block_tags

        logger.info(f"[remote] illust_ranking {mode}")
        return await self._get_illusts(self._papi.illust_ranking, "illusts",
                                       block_tags, 0, 0, skip, limit, 0,
                                       mode=mode.name)

    @auto_retry
    async def image(self, illust: Illust) -> bytes:
        download_quantity = self._conf.pixiv_download_quantity
        custom_domain = self._conf.pixiv_download_custom_domain

        if download_quantity == DownloadQuantity.original:
            if len(illust.meta_pages) > 0:
                url = illust.meta_pages[0].image_urls.original
            else:
                url = illust.meta_single_page.original_image_url
        else:
            url = illust.image_urls.__getattribute__(download_quantity.name)

        if custom_domain is not None:
            url = url.replace("i.pximg.net", custom_domain)

        with BytesIO() as bio:
            await self._papi.download(url, fname=bio)
            content = bio.getvalue()
            content = await self._compressor.compress(content)
            return content
