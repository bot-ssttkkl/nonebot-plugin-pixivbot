import asyncio
import typing
from io import BytesIO

from nonebot import logger
from pixivpy_async import *
from pixivpy_async.error import TokenError

from .abstract_data_source import AbstractDataSource
from .cache_manager import CacheManager
from .compressor import Compressor
from .pkg_context import context
from ...config import Config
from ...errors import QueryError
from ...model import Illust, User, LazyIllust


@context.register_singleton()
class RemoteDataSource(AbstractDataSource):
    _conf: Config = context.require(Config)

    def __init__(self):
        self.user_id = 0

        self.refresh_token = self._conf.pixiv_refresh_token
        self.simultaneous_query = self._conf.pixiv_simultaneous_query
        self.timeout = self._conf.pixiv_query_timeout
        self.proxy = self._conf.pixiv_proxy

        self._compressor = Compressor(enabled=self._conf.pixiv_compression_enabled,
                                      max_size=self._conf.pixiv_compression_max_size,
                                      quantity=self._conf.pixiv_compression_quantity)

        self._cache_manager = CacheManager(
            simultaneous_query=self._conf.pixiv_simultaneous_query)

    async def _refresh(self):
        # Latest app version can be found using GET /v1/application-info/android
        USER_AGENT = "PixivAndroidApp/5.0.234 (Android 11; Pixel 5)"
        REDIRECT_URI = "https://app-api.pixiv.net/web/v1/users/auth/pixiv/callback"
        LOGIN_URL = "https://app-api.pixiv.net/web/v1/login"
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
            logger.debug(f"access_token: {result.access_token}")
            logger.debug(f"refresh_token: {result.refresh_token}")

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
                await asyncio.sleep(result.expires_in * 0.8)
            except asyncio.CancelledError as e:
                raise e
            except Exception as e:
                logger.error(
                    "failed to refresh access token, will retry in 60s.")
                logger.exception(e)
                await asyncio.sleep(60)

    def start(self):
        self._cache_manager = CacheManager(self.simultaneous_query)
        self._pclient = PixivClient(proxy=self.proxy)
        self._papi = AppPixivAPI(client=self._pclient.start())
        self._refresh_daemon_task = asyncio.create_task(self._refresh_daemon())

    async def shutdown(self):
        await self._pclient.close()
        self._refresh_daemon_task.cancel()

    T = typing.TypeVar("T")

    @staticmethod
    async def _flat_page(papi_search_func: typing.Callable,
                         element_list_name: str,
                         element_mapper: typing.Optional[typing.Callable[[
                             typing.Any], T]] = None,
                         element_filter: typing.Optional[typing.Callable[[
                             T], bool]] = None,
                         max_item: int = 2 ** 31,
                         max_page: int = 2 ** 31, **kwargs) -> typing.List[T]:
        cur_page = 0
        flatten = []

        # logger.debug("loading page " + str(cur_page + 1))
        raw_result = await papi_search_func(**kwargs)
        if "error" in raw_result:
            raise QueryError(**raw_result["error"])

        while len(flatten) < max_item and cur_page < max_page:
            for x in raw_result[element_list_name]:
                element = x
                if element_mapper is not None:
                    element = element_mapper(x)
                if element_filter is None or element_filter(element):
                    flatten.append(element)
                    if len(flatten) >= max_item:
                        break
            else:
                next_qs = AppPixivAPI.parse_qs(next_url=raw_result["next_url"])
                if next_qs is None:
                    break

                if 'viewed' in next_qs:
                    # 由于pixivpy-async的illust_recommended的bug，需要删掉这个参数
                    del next_qs['viewed']

                cur_page = cur_page + 1
                # logger.debug("loading page " + str(cur_page + 1))
                raw_result = await papi_search_func(**next_qs)
                if "error" in raw_result:
                    raise QueryError(**raw_result["error"])

        return flatten

    @staticmethod
    async def _get_illusts(papi_search_func: typing.Callable,
                           element_list_name: str,
                           block_tags: typing.Optional[typing.List[str]],
                           min_bookmark: int = 2 ** 31,
                           min_view: int = 2 ** 31,
                           max_item: int = 2 ** 31,
                           max_page: int = 2 ** 31, *args, **kwargs):
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

        illusts = await RemoteDataSource._flat_page(papi_search_func, element_list_name,
                                                    lambda x: Illust.parse_obj(
                                                        x),
                                                    illust_filter, max_item, max_page,
                                                    **kwargs)
        content = []
        broken = 0
        for x in illusts:
            if "limit_unknown_360.png" in x.image_urls.large:
                broken += 1
                content.append(LazyIllust(x.id))
            else:
                content.append(LazyIllust(x.id, x))

        logger.debug(
            f"[RemoteDataSource] {len(illusts)} got, illust_detail of {broken} are missed")

        return content

    async def illust_detail(self, illust_id: int) -> Illust:
        logger.debug(f"[RemoteDataSource] illust_detail {illust_id}")

        content = await self._papi.illust_detail(illust_id)
        if "error" in content:
            raise QueryError(**content["error"])
        return Illust.parse_obj(content["illust"])

    async def search_illust(self, word: str) -> typing.List[LazyIllust]:
        max_item = self._conf.pixiv_random_illust_max_item
        max_page = self._conf.pixiv_random_illust_max_page
        min_bookmark = self._conf.pixiv_random_illust_min_bookmark
        min_view = self._conf.pixiv_random_illust_min_view
        block_tags = self._conf.pixiv_block_tags

        logger.debug(f"[RemoteDataSource] search_illust {word}")
        return await self._get_illusts(self._papi.search_illust, "illusts",
                                       block_tags, min_bookmark, min_view,
                                       max_item, max_page,
                                       word=word)

    async def search_user(self, word: str) -> typing.List[User]:
        logger.debug(f"[RemoteDataSource] search_user {word}")
        content = await self._flat_page(self._papi.search_user, "user_previews",
                                        lambda x: User.parse_obj(
                                            x["user"]),
                                        word=word)
        return content

    async def user_illusts(self, user_id: int = 0) -> typing.List[LazyIllust]:
        if user_id == 0:
            user_id = self.user_id

        max_item = self._conf.pixiv_random_user_illust_max_item
        max_page = self._conf.pixiv_random_user_illust_max_page
        min_bookmark = self._conf.pixiv_random_user_illust_min_bookmark
        min_view = self._conf.pixiv_random_user_illust_min_view
        block_tags = self._conf.pixiv_block_tags

        logger.debug(f"[RemoteDataSource] user_illusts {user_id}")
        return await self._get_illusts(self._papi.user_illusts, "illusts",
                                       block_tags, min_bookmark, min_view,
                                       max_item, max_page,
                                       user_id=user_id)

    async def user_bookmarks(self, user_id: int = 0) -> typing.List[LazyIllust]:
        if user_id == 0:
            user_id = self.user_id

        max_item = self._conf.pixiv_random_bookmark_max_item
        max_page = self._conf.pixiv_random_bookmark_max_page
        min_bookmark = self._conf.pixiv_random_bookmark_min_bookmark
        min_view = self._conf.pixiv_random_bookmark_min_view
        block_tags = self._conf.pixiv_block_tags

        logger.debug(f"[RemoteDataSource] user_bookmarks {user_id}")
        return await self._get_illusts(self._papi.user_bookmarks_illust, "illusts",
                                       block_tags, min_bookmark, min_view,
                                       max_item, max_page,
                                       user_id=user_id)

    async def recommended_illusts(self) -> typing.List[LazyIllust]:
        max_item = self._conf.pixiv_random_recommended_illust_max_item
        max_page = self._conf.pixiv_random_recommended_illust_max_page
        min_bookmark = self._conf.pixiv_random_recommended_illust_min_bookmark
        min_view = self._conf.pixiv_random_recommended_illust_min_view
        block_tags = self._conf.pixiv_block_tags

        logger.debug(f"[RemoteDataSource] recommended_illusts")
        return await self._get_illusts(self._papi.recommended_illusts, "illusts",
                                       block_tags, min_bookmark, min_view,
                                       max_item, max_page)

    async def related_illusts(self, illust_id: int) -> typing.List[LazyIllust]:
        max_item = self._conf.pixiv_random_related_illust_max_item
        max_page = self._conf.pixiv_random_related_illust_max_page
        min_bookmark = self._conf.pixiv_random_related_illust_min_bookmark
        min_view = self._conf.pixiv_random_related_illust_min_view
        block_tags = self._conf.pixiv_block_tags

        logger.debug(f"[RemoteDataSource] related_illusts {illust_id}")
        return await self._get_illusts(self._papi.illust_related, "illusts",
                                       block_tags, min_bookmark, min_view,
                                       max_item, max_page,
                                       illust_id=illust_id)

    async def illust_ranking(self, mode: str = 'day') -> typing.List[LazyIllust]:
        max_item = self._conf.pixiv_ranking_fetch_item
        block_tags = self._conf.pixiv_block_tags

        logger.debug(
            f"[RemoteDataSource] illust_ranking {mode}")
        return await self._get_illusts(self._papi.illust_ranking, "illusts",
                                       block_tags,
                                       max_item=max_item,
                                       mode=mode)

    async def image(self, illust: Illust) -> bytes:
        download_quantity = self._conf.pixiv_download_quantity
        custom_domain = self._conf.pixiv_download_custom_domain

        if download_quantity == "original":
            if len(illust.meta_pages) > 0:
                url = illust.meta_pages[0].image_urls.original
            else:
                url = illust.meta_single_page.original_image_url
        else:
            url = illust.image_urls.__getattribute__(download_quantity)

        if custom_domain is not None:
            url = url.replace("i.pximg.net", custom_domain)

        with BytesIO() as bio:
            await self._papi.download(url, fname=bio)
            content = bio.getvalue()
            content = await self._compressor.compress(content)
            return content
