import asyncio
import functools
import typing
from concurrent.futures.thread import ThreadPoolExecutor
from datetime import datetime
from io import BytesIO

import bson
import nonebot
from PIL import Image, ImageFile
from nonebot import logger
from pixivpy_async import *
from pixivpy_async.error import TokenError

from .cache_manager import CacheManager
from .model.Illust import Illust
from .model.User import User
from .errors import QueryError


class PixivDataSource:
    db_name: str
    timeout: int
    compression_enabled: bool
    compression_max_size: int
    compression_quantity: int

    _client: PixivClient
    _api: AppPixivAPI
    _cache_manager: CacheManager
    _compress_executor: ThreadPoolExecutor

    async def initialize(self, db_name, proxy, timeout=60,
                         compression_enabled=False, compression_max_size=None,
                         compression_quantity=None):
        self._client = PixivClient(proxy=proxy)
        self._api = AppPixivAPI(client=self._client.start())
        self._cache_manager = CacheManager()
        self._cache_manager.start()

        self.db_name = db_name
        self.timeout = timeout
        self.compression_enabled = compression_enabled
        self.compression_max_size = compression_max_size
        self.compression_quantity = compression_quantity
        if compression_enabled:
            self._compress_executor = ThreadPoolExecutor(max_workers=2)

    async def shutdown(self):
        await self._client.close()
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
        result = await self._api.requests_(method="POST", url=AUTH_TOKEN_URL, data=data,
                                           headers={"User-Agent": USER_AGENT},
                                           auth=False)
        if result.has_error:
            raise TokenError(None, result)
        else:
            self._api.set_auth(result.access_token, result.refresh_token)
            return result

    T = typing.TypeVar("T")

    @staticmethod
    async def _flat_page(search_func: typing.Callable,
                         element_list_name: str,
                         element_mapper: typing.Optional[typing.Callable[[typing.Any], T]] = None,
                         element_filter: typing.Optional[typing.Callable[[T], bool]] = None,
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

    @staticmethod
    def _illust_filter_factory(block_tags: typing.Optional[typing.List[str]],
                               min_bookmark: int = 2 ** 31,
                               min_view: int = 2 ** 31):
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

        return illust_filter

    @property
    def _db(self):
        db_conn = nonebot.require("nonebot_plugin_navicat").mongodb_client
        return db_conn[self.db_name]

    def _cache_loader_factory(self, collection_name: str,
                              arg_name: str,
                              arg: typing.Any,
                              content_key: str,
                              content_mapper: typing.Optional[typing.Callable] = None):
        async def cache_loader():
            cache = await self._db[collection_name].find_one({arg_name: arg})
            if cache is not None:
                return content_mapper(cache[content_key]) if content_mapper is not None else cache[content_key]
            else:
                return None

        return cache_loader

    def _cache_updater_factory(self, collection_name: str,
                               arg_name: str,
                               arg: typing.Any,
                               content_key: str,
                               content_mapper: typing.Optional[typing.Callable] = None):
        async def cache_updater(content):
            await self._db[collection_name].update_one(
                {arg_name: arg},
                {"$set": {
                    content_key: content_mapper(content) if content_mapper is not None else content,
                    "update_time": datetime.now()
                }},
                upsert=True
            )

        return cache_updater

    async def search_illust(self, word: str,
                            max_item: int = 2 ** 31,
                            max_page: int = 2 ** 31,
                            block_tags: typing.Optional[typing.List[typing.Union[Illust.Tag, str]]] = None,
                            min_bookmark: int = 0,
                            min_view: int = 0) -> typing.List[Illust]:
        async def remote_fetcher():
            logger.debug("cache not found or out of date, search illust from remote")
            content = await self._flat_page(self._api.search_illust, "illusts",
                                            lambda x: Illust.parse_obj(x),
                                            self._illust_filter_factory(block_tags, min_bookmark, min_view),
                                            max_item, max_page,
                                            word=word)
            return content

        return await self._cache_manager.get(
            identifier=(0, word),
            cache_loader=self._cache_loader_factory("search_illust_cache", "word", word, "illusts",
                                                    lambda content: [Illust.parse_obj(x) for x in content]),
            remote_fetcher=remote_fetcher,
            cache_updater=self._cache_updater_factory("search_illust_cache", "word", word, "illusts",
                                                      lambda content: [x.dict() for x in content]),
            timeout=self.timeout
        )

    async def search_user(self, word: str,
                          max_item: int = 2 ** 31,
                          max_page: int = 2 ** 31) -> typing.List[User]:
        async def remote_fetcher():
            logger.debug("cache not found or out of date, search user from remote")
            content = await self._flat_page(self._api.search_user, "user_previews",
                                            lambda x: User.parse_obj(x["user"]),
                                            max_item=max_item, max_page=max_page, word=word)
            return content

        return await self._cache_manager.get(
            identifier=(1, word),
            cache_loader=self._cache_loader_factory("search_user_cache", "word", word, "users",
                                                    lambda content: [User.parse_obj(x) for x in content]),
            remote_fetcher=remote_fetcher,
            cache_updater=self._cache_updater_factory("search_user_cache", "word", word, "users",
                                                      lambda content: [x.dict() for x in content]),
            timeout=self.timeout
        )

    async def user_illusts(self, user_id: int = 0,
                           max_item: int = 2 ** 31,
                           max_page: int = 2 ** 31,
                           block_tags: typing.Optional[typing.List[typing.Union[Illust.Tag, str]]] = None,
                           min_bookmark: int = 0,
                           min_view: int = 0) -> typing.List[Illust]:
        if user_id == 0:
            user_id = self._api.user_id

        async def remote_fetcher():
            logger.debug("cache not found or out of date, get user illusts from remote")
            content = await self._flat_page(self._api.user_illusts, "illusts",
                                            lambda x: Illust.parse_obj(x),
                                            self._illust_filter_factory(block_tags, min_bookmark, min_view),
                                            max_item, max_page,
                                            user_id=user_id)
            return content

        return await self._cache_manager.get(
            identifier=(2, user_id),
            cache_loader=self._cache_loader_factory("user_illusts_cache", "user_id", user_id, "illusts",
                                                    lambda content: [Illust.parse_obj(x) for x in content]),
            remote_fetcher=remote_fetcher,
            cache_updater=self._cache_updater_factory("user_illusts_cache", "user_id", user_id, "illusts",
                                                      lambda content: [x.dict() for x in content]),
            timeout=self.timeout
        )

    async def user_bookmarks(self, user_id: int = 0,
                             max_item: int = 2 ** 31,
                             max_page: int = 2 ** 31,
                             block_tags: typing.Optional[typing.List[typing.Union[Illust.Tag, str]]] = None,
                             min_bookmark: int = 0,
                             min_view: int = 0) -> typing.List[Illust]:
        if user_id == 0:
            user_id = self._api.user_id

        async def remote_fetcher():
            logger.debug("cache not found or out of date, get user bookmarks from remote")
            content = await self._flat_page(self._api.user_bookmarks_illust, "illusts",
                                            lambda x: Illust.parse_obj(x),
                                            self._illust_filter_factory(block_tags, min_bookmark, min_view),
                                            max_item, max_page, user_id=user_id)
            return content

        return await self._cache_manager.get(
            identifier=(3,),
            cache_loader=self._cache_loader_factory("other_cache", "type", "user_bookmarks", "illusts",
                                                    lambda content: [Illust.parse_obj(x) for x in content]),
            remote_fetcher=remote_fetcher,
            cache_updater=self._cache_updater_factory("other_cache", "type", "user_bookmarks", "illusts",
                                                      lambda content: [x.dict() for x in content]),
            timeout=self.timeout
        )

    async def recommended_illusts(self, max_item: int = 2 ** 31,
                                  max_page: int = 2 ** 31,
                                  block_tags: typing.Optional[typing.List[typing.Union[Illust.Tag, str]]] = None,
                                  min_bookmark: int = 0,
                                  min_view: int = 0) -> typing.List[Illust]:
        async def remote_fetcher():
            logger.debug("cache not found or out of date, get recommended illusts from remote")
            content = await self._flat_page(self._api.illust_recommended, "illusts",
                                            lambda x: Illust.parse_obj(x),
                                            self._illust_filter_factory(block_tags, min_bookmark, min_view),
                                            max_item, max_page)
            return content

        return await self._cache_manager.get(
            identifier=(4,),
            cache_loader=self._cache_loader_factory("other_cache", "type", "recommended_illusts", "illusts",
                                                    lambda content: [Illust.parse_obj(x) for x in content]),
            remote_fetcher=remote_fetcher,
            cache_updater=self._cache_updater_factory("other_cache", "type", "recommended_illusts", "illusts",
                                                      lambda content: [x.dict() for x in content]),
            timeout=self.timeout
        )

    async def illust_ranking(self, mode: str = 'day',
                             max_item: int = 2 ** 31,
                             max_page: int = 2 ** 31,
                             block_tags: typing.Optional[typing.List[typing.Union[Illust.Tag, str]]] = None,
                             min_bookmark: int = 0,
                             min_view: int = 0) -> typing.List[Illust]:
        async def remote_fetcher():
            logger.debug("cache not found or out of date, get illust ranking from remote")
            content = await self._flat_page(self._api.illust_ranking, "illusts",
                                            lambda x: Illust.parse_obj(x),
                                            self._illust_filter_factory(block_tags, min_bookmark, min_view),
                                            max_item, max_page, mode=mode)
            return content

        return await self._cache_manager.get(
            identifier=(5,),
            cache_loader=self._cache_loader_factory("illust_ranking_cache", "mode", mode, "illusts",
                                                    lambda content: [Illust.parse_obj(x) for x in content]),
            remote_fetcher=remote_fetcher,
            cache_updater=self._cache_updater_factory("illust_ranking_cache", "mode", mode, "illusts",
                                                      lambda content: [x.dict() for x in content]),
            timeout=self.timeout
        )

    async def illust_detail(self, illust_id: int) -> Illust:
        async def remote_fetcher():
            logger.debug("cache not found or out of date, get illust detail from remote")
            content = await self._api.illust_detail(illust_id)
            if "error" in content:
                raise QueryError(**content["error"])
            return Illust.parse_obj(content["illust"])

        return await self._cache_manager.get(
            identifier=(6, illust_id),
            cache_loader=self._cache_loader_factory("illust_detail_cache", "illust.id", illust_id, "illust",
                                                    lambda content: Illust.parse_obj(content)),
            remote_fetcher=remote_fetcher,
            cache_updater=self._cache_updater_factory("illust_detail_cache", "illust.id", illust_id, "illust",
                                                      lambda content: content.dict()),
            timeout=self.timeout
        )

    async def download(self, illust: Illust,
                       download_quantity: str = 'original',
                       custom_domain: str = None) -> bytes:
        async def remote_fetcher():
            logger.debug("cache not found or out of date, download from remote")

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
                await self._api.download(url, fname=bio)
                content = bio.getvalue()
                if self.compression_enabled:
                    loop = asyncio.get_running_loop()
                    task = loop.run_in_executor(self._compress_executor, functools.partial(self._compress, content))
                    return await task
                else:
                    return content

        return await self._cache_manager.get(
            identifier=(7, illust.id),
            cache_loader=self._cache_loader_factory("download_cache", "illust_id", illust.id, "content", None),
            remote_fetcher=remote_fetcher,
            cache_updater=self._cache_updater_factory("download_cache", "illust_id", illust.id, "content",
                                                      lambda content: bson.binary.Binary(content)),
            timeout=self.timeout
        )

    def _compress(self, content: bytes) -> bytes:
        p = ImageFile.Parser()
        p.feed(content)
        img = p.close()

        w, h = img.size
        if w > self.compression_max_size or h > self.compression_max_size:
            ratio = min(self.compression_max_size / w, self.compression_max_size / h)
            img_cp = img.resize((int(ratio * w), int(ratio * h)), Image.ANTIALIAS)
        else:
            img_cp = img.copy()
        img_cp = img_cp.convert("RGB")

        with BytesIO() as bio:
            img_cp.save(bio, format="JPEG", optimize=True, quantity=self.compression_quantity)
            return bio.getvalue()


data_source = PixivDataSource()

__all__ = ('data_source', 'PixivDataSource')
