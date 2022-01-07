import asyncio
import functools
import typing
from concurrent.futures.thread import ThreadPoolExecutor
from datetime import datetime, timedelta
from io import BytesIO

import bson
from apscheduler.triggers.date import DateTrigger
from nonebot import get_driver, logger, require
from PIL import Image, ImageFile
from pixivpy_async import *
from pixivpy_async.error import TokenError

from ..config import conf
from ..model import Illust, LazyIllust, User
from ..utils.errors import QueryError
from .cache_data_source import CacheDataSource
from .cache_manager import CacheManager


class PixivDataSource:
    proxy: str
    timeout: int
    compression_enabled: bool
    compression_max_size: int
    compression_quantity: int
    user_id: int

    _pclient: PixivClient
    _papi: AppPixivAPI
    _cache_data_souce: CacheDataSource
    _cache_manager: CacheManager
    _compress_executor: ThreadPoolExecutor

    def __init__(self, proxy=None, timeout=60,
                 compression_enabled=False, compression_max_size=None,
                 compression_quantity=None):
        self.proxy = proxy
        self.timeout = timeout
        self.compression_enabled = compression_enabled
        self.compression_max_size = compression_max_size
        self.compression_quantity = compression_quantity
        if compression_enabled:
            self._compress_executor = ThreadPoolExecutor(
                2, "pixiv_bot_compression_thread")

    def start(self):
        self._pclient = PixivClient(proxy=self.proxy)
        self._papi = AppPixivAPI(client=self._pclient.start())
        self._cache_manager = CacheManager()
        self._cache_manager.start()
        self._cache_data_souce = CacheDataSource()

    async def shutdown(self):
        await self._pclient.close()
        self._cache_manager.stop()

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

    T = typing.TypeVar("T")

    @staticmethod
    async def _flat_page(search_func: typing.Callable,
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
        raw_result = await search_func(**kwargs)
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
                    del next_qs['viewed']  # 由于pixivpy-async的illust_recommended的bug，需要删掉这个参数

                cur_page = cur_page + 1
                # logger.debug("loading page " + str(cur_page + 1))
                raw_result = await search_func(**next_qs)
                if "error" in raw_result:
                    raise QueryError(**raw_result["error"])

        return flatten

    def _lazy_illusts_cache_loader_factory(self, cache_loader, *args, **kwargs):
        async def lazy_cache_loader():
            cache = await cache_loader(*args, **kwargs)
            if cache is not None:
                return [LazyIllust(x, self) for x in cache]
            else:
                return None

        return lazy_cache_loader

    def _lazy_illusts_remote_fetcher_factory(self, search_func: typing.Callable,
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

        async def remote_fetcher():
            logger.info(f"cache not found, {search_func.__name__} from remote")
            content = await self._flat_page(search_func, element_list_name,
                                            lambda x: Illust.parse_obj(x),
                                            illust_filter, max_item, max_page,
                                            *args, **kwargs)
            return [LazyIllust(x.id, self, x) for x in content]

        return remote_fetcher

    def _lazy_illusts_cache_updater_factory(self, cache_updater, *args, **kwargs):
        async def lazy_cache_updater(content: typing.List[LazyIllust]):
            await cache_updater(*args, **kwargs, content=[x.id for x in content])

            for x in content:
                # detail may be broken
                if x.content is not None and "limit_unknown_360.png" not in x.content.image_urls.large:
                    await self._cache_data_souce.update_illust_detail(x.content)

        return lazy_cache_updater

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

    def illust_detail_local(self, illust_id: int):
        return self._cache_data_souce.illust_detail(illust_id)

    async def search_illust(self, word: str,
                            max_item: int = 2 ** 31,
                            max_page: int = 2 ** 31,
                            block_tags: typing.Optional[typing.List[typing.Union[Illust.Tag, str]]] = None,
                            min_bookmark: int = 0,
                            min_view: int = 0) -> typing.List[LazyIllust]:
        return await self._cache_manager.get(
            identifier=(0, word),
            cache_loader=self._lazy_illusts_cache_loader_factory(
                self._cache_data_souce.search_illust, word=word),
            remote_fetcher=self._lazy_illusts_remote_fetcher_factory(self._papi.search_illust, "illusts",
                                                                     block_tags, min_bookmark, min_view,
                                                                     max_item, max_page,
                                                                     word=word),
            cache_updater=self._lazy_illusts_cache_updater_factory(
                self._cache_data_souce.update_search_illust, word=word),
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
            cache_loader=lambda: self._cache_data_souce.search_user(word),
            remote_fetcher=remote_fetcher,
            cache_updater=lambda x: self._cache_data_souce.update_search_user(
                word, x),
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
            cache_loader=self._lazy_illusts_cache_loader_factory(
                self._cache_data_souce.user_illusts, user_id=user_id),
            remote_fetcher=self._lazy_illusts_remote_fetcher_factory(self._papi.user_illusts, "illusts",
                                                                     block_tags, min_bookmark, min_view,
                                                                     max_item, max_page,
                                                                     user_id=user_id),
            cache_updater=self._lazy_illusts_cache_updater_factory(
                self._cache_data_souce.update_user_illusts, user_id=user_id),
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
            cache_loader=self._lazy_illusts_cache_loader_factory(
                self._cache_data_souce.user_bookmarks, user_id=user_id),
            remote_fetcher=self._lazy_illusts_remote_fetcher_factory(self._papi.user_bookmarks_illust, "illusts",
                                                                     block_tags, min_bookmark, min_view,
                                                                     max_item, max_page,
                                                                     user_id=user_id),
            cache_updater=self._lazy_illusts_cache_updater_factory(
                self._cache_data_souce.update_user_bookmarks, user_id=user_id),
            timeout=self.timeout
        )

    async def recommended_illusts(self, max_item: int = 2 ** 31,
                                  max_page: int = 2 ** 31,
                                  block_tags: typing.Optional[typing.List[typing.Union[Illust.Tag, str]]] = None,
                                  min_bookmark: int = 0,
                                  min_view: int = 0) -> typing.List[LazyIllust]:
        return await self._cache_manager.get(
            identifier=(4,),
            cache_loader=self._lazy_illusts_cache_loader_factory(
                self._cache_data_souce.recommended_illusts),
            remote_fetcher=self._lazy_illusts_remote_fetcher_factory(self._papi.illust_recommended, "illusts",
                                                                     block_tags, min_bookmark, min_view,
                                                                     max_item, max_page),
            cache_updater=self._lazy_illusts_cache_updater_factory(
                self._cache_data_souce.update_recommended_illusts),
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
            cache_loader=self._lazy_illusts_cache_loader_factory(
                self._cache_data_souce.illust_ranking, mode=mode),
            remote_fetcher=self._lazy_illusts_remote_fetcher_factory(self._papi.illust_ranking, "illusts",
                                                                     block_tags, min_bookmark, min_view,
                                                                     max_item, max_page,
                                                                     mode=mode),
            cache_updater=self._lazy_illusts_cache_updater_factory(
                self._cache_data_souce.update_illust_ranking, mode=mode),
            timeout=self.timeout
        )

    async def download(self, illust: typing.Union[Illust, LazyIllust],
                       download_quantity: str = 'original',
                       custom_domain: str = None) -> bytes:
        async def remote_fetcher():
            nonlocal illust

            logger.info("cache not found, download from remote")

            if isinstance(illust, LazyIllust):
                illust = await illust.get()

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
                if self.compression_enabled:
                    loop = asyncio.get_running_loop()
                    task = loop.run_in_executor(
                        self._compress_executor, functools.partial(self._compress, content))
                    return await task
                else:
                    return content

        return await self._cache_manager.get(
            identifier=(7, illust.id),
            cache_loader=lambda: self._cache_data_souce.download(illust.id),
            remote_fetcher=remote_fetcher,
            cache_updater=lambda x: self._cache_data_souce.update_download(
                illust.id, x),
            timeout=self.timeout
        )

    def _compress(self, content: bytes) -> bytes:
        p = ImageFile.Parser()
        p.feed(content)
        img = p.close()

        w, h = img.size
        if w > self.compression_max_size or h > self.compression_max_size:
            ratio = min(self.compression_max_size / w,
                        self.compression_max_size / h)
            img_cp = img.resize(
                (int(ratio * w), int(ratio * h)), Image.ANTIALIAS)
        else:
            img_cp = img.copy()
        img_cp = img_cp.convert("RGB")

        with BytesIO() as bio:
            img_cp.save(bio, format="JPEG", optimize=True,
                        quantity=self.compression_quantity)
            return bio.getvalue()


pixiv_data_source = PixivDataSource(proxy=conf.pixiv_proxy,
                              timeout=conf.pixiv_query_timeout,
                              compression_enabled=conf.pixiv_compression_enabled,
                              compression_max_size=conf.pixiv_compression_max_size,
                              compression_quantity=conf.pixiv_compression_quantity)

get_driver().on_startup(pixiv_data_source.start)
get_driver().on_shutdown(pixiv_data_source.shutdown)


@get_driver().on_startup
async def do_refresh():
    try:
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

        next_time = datetime.now() + timedelta(seconds=60)
    finally:
        scheduler = require("nonebot_plugin_apscheduler").scheduler
        scheduler.add_job(do_refresh, trigger=DateTrigger(next_time))


__all__ = ('PixivDataSource', "pixiv_data_source", "LazyIllust")
