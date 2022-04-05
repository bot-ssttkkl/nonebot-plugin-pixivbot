import asyncio
import functools
import typing
from datetime import datetime, timedelta
from io import BytesIO

from apscheduler.triggers.date import DateTrigger
from nonebot import get_driver, logger, require
from pixivpy_async import *
from pixivpy_async.error import TokenError

from .cache_data_source import CacheDataSource
from .cache_manager import CacheManager
from .compressor import Compressor
from .pkg_context import context
from ..config import Config
from ..errors import QueryError
from ..model import Illust, User, LazyIllust


conf: Config = context.require(Config)


@context.export_singleton(simultaneous_query=conf.pixiv_simultaneous_query,
                          timeout=conf.pixiv_query_timeout,
                          proxy=conf.pixiv_proxy)
class PixivDataSource:
    _cache_data_souce = context.require(CacheDataSource)
    _compressor = context.require(Compressor)

    def __init__(self, simultaneous_query, timeout, proxy):
        self.user_id = 0

        self.simultaneous_query = simultaneous_query
        self.timeout = timeout
        self.proxy = proxy

    def start(self):
        self._cache_manager = CacheManager(self.simultaneous_query)
        self._pclient = PixivClient(proxy=self.proxy)
        self._papi = AppPixivAPI(client=self._pclient.start())

    async def shutdown(self):
        await self._pclient.close()

    async def refresh(self, refresh_token: str):
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
            return result

    def invalidate_cache(self):
        return self._cache_data_souce.invalidate_cache()

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

    def _make_illusts_remote_fetcher(self, papi_search_func: typing.Callable,
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

        async def remote_fetcher() -> typing.List[LazyIllust]:
            logger.info(
                f"cache not found, {papi_search_func.__name__} from remote")
            illusts = await self._flat_page(papi_search_func, element_list_name,
                                            lambda x: Illust.parse_obj(x),
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

            logger.info(
                f"{len(illusts)} got, illust_detail of {broken} are missed")

            return content

        return remote_fetcher

    async def illust_detail(self, illust_id: int) -> Illust:
        async def remote_fetcher():
            logger.info("cache not found, get illust detail from remote")
            content = await self._papi.illust_detail(illust_id)
            if "error" in content:
                raise QueryError(**content["error"])
            return Illust.parse_obj(content["illust"])

        return await self._cache_manager.get(
            identifier=(6, illust_id),
            cache_loader=lambda: self._cache_data_souce.illust_detail(
                illust_id),
            remote_fetcher=remote_fetcher,
            cache_updater=self._cache_data_souce.update_illust_detail,
            timeout=self.timeout
        )

    async def search_illust(self, word: str,
                            max_item: int = 2 ** 31,
                            max_page: int = 2 ** 31,
                            block_tags: typing.Optional[typing.List[typing.Union[Illust.Tag, str]]] = None,
                            min_bookmark: int = 0,
                            min_view: int = 0) -> typing.List[LazyIllust]:
        return await self._cache_manager.get(
            identifier=(0, word),
            cache_loader=functools.partial(
                self._cache_data_souce.search_illust, word=word),
            remote_fetcher=self._make_illusts_remote_fetcher(self._papi.search_illust, "illusts",
                                                             block_tags, min_bookmark, min_view,
                                                             max_item, max_page,
                                                             word=word),
            cache_updater=lambda content: self._cache_data_souce.update_search_illust(
                word, content),
            timeout=self.timeout
        )

    async def search_user(self, word: str,
                          max_item: int = 2 ** 31,
                          max_page: int = 2 ** 31) -> typing.List[User]:
        async def remote_fetcher():
            logger.info(
                "cache not found or out of date, search user from remote")
            content = await self._flat_page(self._papi.search_user, "user_previews",
                                            lambda x: User.parse_obj(
                                                x["user"]),
                                            max_item=max_item, max_page=max_page, word=word)
            return content

        return await self._cache_manager.get(
            identifier=(1, word),
            cache_loader=functools.partial(
                self._cache_data_souce.search_user, word),
            remote_fetcher=remote_fetcher,
            cache_updater=lambda content: self._cache_data_souce.update_search_user(
                word, content),
            timeout=self.timeout
        )

    async def user_illusts(self, user_id: int = 0,
                           max_item: int = 2 ** 31,
                           max_page: int = 2 ** 31,
                           block_tags: typing.Optional[typing.List[typing.Union[Illust.Tag, str]]] = None,
                           min_bookmark: int = 0,
                           min_view: int = 0) -> typing.List[LazyIllust]:
        if user_id == 0:
            user_id = self.user_id

        return await self._cache_manager.get(
            identifier=(2, user_id),
            cache_loader=functools.partial(
                self._cache_data_souce.user_illusts, user_id=user_id),
            remote_fetcher=self._make_illusts_remote_fetcher(self._papi.user_illusts, "illusts",
                                                             block_tags, min_bookmark, min_view,
                                                             max_item, max_page,
                                                             user_id=user_id),
            cache_updater=lambda content: self._cache_data_souce.update_user_illusts(
                user_id, content),
            timeout=self.timeout
        )

    async def user_bookmarks(self, user_id: int = 0,
                             max_item: int = 2 ** 31,
                             max_page: int = 2 ** 31,
                             block_tags: typing.Optional[typing.List[typing.Union[Illust.Tag, str]]] = None,
                             min_bookmark: int = 0,
                             min_view: int = 0) -> typing.List[LazyIllust]:
        if user_id == 0:
            user_id = self.user_id

        return await self._cache_manager.get(
            identifier=(3, user_id),
            cache_loader=functools.partial(
                self._cache_data_souce.user_bookmarks, user_id=user_id),
            remote_fetcher=self._make_illusts_remote_fetcher(self._papi.user_bookmarks_illust, "illusts",
                                                             block_tags, min_bookmark, min_view,
                                                             max_item, max_page,
                                                             user_id=user_id),
            cache_updater=lambda content: self._cache_data_souce.update_user_bookmarks(
                user_id, content),
            timeout=self.timeout
        )

    async def recommended_illusts(self, max_item: int = 2 ** 31,
                                  max_page: int = 2 ** 31,
                                  block_tags: typing.Optional[typing.List[typing.Union[Illust.Tag, str]]] = None,
                                  min_bookmark: int = 0,
                                  min_view: int = 0) -> typing.List[LazyIllust]:
        return await self._cache_manager.get(
            identifier=(4,),
            cache_loader=self._cache_data_souce.recommended_illusts,
            remote_fetcher=self._make_illusts_remote_fetcher(self._papi.illust_recommended, "illusts",
                                                             block_tags, min_bookmark, min_view,
                                                             max_item, max_page),
            cache_updater=self._cache_data_souce.update_recommended_illusts,
            timeout=self.timeout
        )

    async def related_illusts(self, illust_id: int, max_item: int = 2 ** 31,
                              max_page: int = 2 ** 31,
                              block_tags: typing.Optional[typing.List[typing.Union[Illust.Tag, str]]] = None,
                              min_bookmark: int = 0,
                              min_view: int = 0) -> typing.List[LazyIllust]:
        return await self._cache_manager.get(
            identifier=(8, illust_id),
            cache_loader=functools.partial(
                self._cache_data_souce.related_illusts, illust_id=illust_id),
            remote_fetcher=self._make_illusts_remote_fetcher(self._papi.illust_related, "illusts",
                                                             block_tags, min_bookmark, min_view,
                                                             max_item, max_page, illust_id=illust_id),
            cache_updater=lambda content: self._cache_data_souce.update_related_illusts(
                illust_id, content),
            timeout=self.timeout
        )

    async def illust_ranking(self, mode: str = 'day',
                             max_item: int = 2 ** 31,
                             max_page: int = 2 ** 31,
                             block_tags: typing.Optional[typing.List[typing.Union[Illust.Tag, str]]] = None,
                             min_bookmark: int = 0,
                             min_view: int = 0) -> typing.List[LazyIllust]:
        return await self._cache_manager.get(
            identifier=(5, mode),
            cache_loader=functools.partial(
                self._cache_data_souce.illust_ranking, mode=mode),
            remote_fetcher=self._make_illusts_remote_fetcher(self._papi.illust_ranking, "illusts",
                                                             block_tags, min_bookmark, min_view,
                                                             max_item, max_page,
                                                             mode=mode),
            cache_updater=lambda content: self._cache_data_souce.update_illust_ranking(
                mode, content),
            timeout=self.timeout
        )

    async def download(self, illust: Illust,
                       download_quantity: str = 'original',
                       custom_domain: str = None) -> bytes:
        async def remote_fetcher():
            nonlocal illust

            logger.info("cache not found, download from remote")

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

        return await self._cache_manager.get(
            identifier=(7, illust.id),
            cache_loader=lambda: self._cache_data_souce.download(illust.id),
            remote_fetcher=remote_fetcher,
            cache_updater=lambda content: self._cache_data_souce.update_download(
                illust.id, content),
            timeout=self.timeout
        )


pixiv_data_source = context.require(PixivDataSource)

get_driver().on_startup(pixiv_data_source.start)
get_driver().on_shutdown(pixiv_data_source.shutdown)


@get_driver().on_startup
async def do_refresh():
    next_time = datetime.now() + timedelta(seconds=60)
    try:
        conf = context.require(Config)
        result = await pixiv_data_source.refresh(conf.pixiv_refresh_token)
        logger.success(
            f"refresh access token successfully. new token expires in {result.expires_in} seconds.")
        logger.debug(f"access_token: {result.access_token}")
        logger.debug(f"refresh_token: {result.refresh_token}")

        # maybe the refresh token will be changed (even thought i haven't seen it yet)
        if result.refresh_token != conf.pixiv_refresh_token:
            conf.pixiv_refresh_token = result.refresh_token
            logger.warning(
                f"refresh token has been changed: {result.refresh_token}")

        next_time = datetime.now() + timedelta(seconds=result.expires_in * 0.8)
    except Exception as e:
        logger.error("failed to refresh access token, will retry in 60s.")
        logger.exception(e)
    finally:
        scheduler = require("nonebot_plugin_apscheduler").scheduler
        scheduler.add_job(do_refresh, trigger=DateTrigger(next_time))


__all__ = ('PixivDataSource', )
