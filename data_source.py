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
from .query_error import QueryError


class PixivDataSource:
    _client: PixivClient = None
    _api: AppPixivAPI = None
    _cache_manager: CacheManager = None
    _compress_executor: ThreadPoolExecutor = None
    cache_database_name = ""

    async def initialize(self):
        self._client = PixivClient(proxy="socks5://127.0.0.1:7890")
        self._api = AppPixivAPI(client=self._client.start())
        self._cache_manager = CacheManager()
        self._cache_manager.start()
        self._compress_executor = ThreadPoolExecutor(max_workers=2)

    async def shutdown(self):
        await self._client.close()
        self._cache_manager.stop()

    def api(self) -> AppPixivAPI:
        return self._api

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

    @staticmethod
    async def _flat_page(search_func: typing.Callable,
                         element_list_name: str,
                         element_filter: typing.Optional[typing.Callable[[typing.Any], bool]] = None,
                         max_item: int = 2 ** 31,
                         max_page: int = 2 ** 31, **kwargs) -> typing.List[typing.Any]:
        cur_page = 0
        flatten = []

        # logger.debug("loading page " + str(cur_page + 1))
        raw_result = await search_func(**kwargs)
        if "error" in raw_result:
            raise QueryError(**raw_result["error"])

        while len(flatten) < max_item and cur_page < max_page:
            for x in raw_result[element_list_name]:
                if element_filter is None or element_filter(x):
                    flatten.append(x)
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
    def make_illust_filter(block_tags: typing.List[str],
                           min_bookmark: int = 2 ** 31,
                           min_view: int = 2 ** 31):
        def illust_filter(illust: Illust) -> bool:
            # 标签过滤
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

    def _db(self):
        db_conn = nonebot.require("nonebot_plugin_navicat").mongodb_client
        return db_conn[self.cache_database_name]

    def _cache_loader_factory(self, collection_name: str,
                              arg_name: str,
                              arg: typing.Any,
                              content_key: str,
                              content_mapper: typing.Optional[typing.Callable] = None):
        async def cache_loader():
            cache = await self._db()[collection_name].find_one({arg_name: arg})
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
            await self._db()[collection_name].update_one(
                {arg_name: arg},
                {"$set": {
                    content_key: content_mapper(content) if content_mapper is not None else content,
                    "update_time": datetime.now()
                }},
                upsert=True
            )

        return cache_updater

    async def search_illust(self, word: str,
                            illust_filter: typing.Optional[typing.Callable[[Illust], bool]] = None,
                            max_item: int = 2 ** 31,
                            max_page: int = 2 ** 31) -> typing.List[Illust]:
        async def remote_fetcher():
            logger.debug("cache not found or out of date, search illust from remote")
            content = await self._flat_page(self._api.search_illust, "illusts", illust_filter,
                                            max_item, max_page, word=word)
            return [Illust.parse_obj(x) for x in content]

        return await self._cache_manager.get(
            identifier=(0, word),
            cache_loader=self._cache_loader_factory("search_illust_cache", "word", word, "illusts",
                                                    lambda content: [Illust.parse_obj(x) for x in content]),
            remote_fetcher=remote_fetcher,
            cache_updater=self._cache_updater_factory("search_illust_cache", "word", word, "illusts",
                                                      lambda content: [x.dict() for x in content]),
            timeout=60
        )

    async def search_user(self, word: str,
                          max_item: int = 2 ** 31,
                          max_page: int = 2 ** 31) -> typing.List[User]:

        async def remote_fetcher():
            logger.debug("cache not found or out of date, search user from remote")
            content = await self._flat_page(self._api.search_user, "user_previews", None,
                                            max_item, max_page, word=word)
            return [User.parse_obj(x["user"]) for x in content]

        return await self._cache_manager.get(
            identifier=(1, word),
            cache_loader=self._cache_loader_factory("search_user_cache", "word", word, "users",
                                                    lambda content: [User.parse_obj(x) for x in content]),
            remote_fetcher=remote_fetcher,
            cache_updater=self._cache_updater_factory("search_user_cache", "word", word, "users",
                                                      lambda content: [x.dict() for x in content]),
            timeout=60
        )

    async def user_illusts(self, user_id: int = 0,
                           illust_filter: typing.Optional[typing.Callable[[Illust], bool]] = None,
                           max_item: int = 2 ** 31,
                           max_page: int = 2 ** 31) -> typing.List[Illust]:
        if user_id == 0:
            user_id = self._api.user_id

        async def remote_fetcher():
            logger.debug("cache not found or out of date, get user illusts from remote")
            content = await self._flat_page(self._api.user_illusts, "illusts", illust_filter, max_item, max_page,
                                            user_id=user_id)
            return [Illust.parse_obj(x) for x in content]

        return await self._cache_manager.get(
            identifier=(2, user_id),
            cache_loader=self._cache_loader_factory("user_illusts_cache", "user_id", user_id, "illusts",
                                                    lambda content: [Illust.parse_obj(x) for x in content]),
            remote_fetcher=remote_fetcher,
            cache_updater=self._cache_updater_factory("user_illusts_cache", "user_id", user_id, "illusts",
                                                      lambda content: [x.dict() for x in content]),
            timeout=60
        )

    async def user_bookmarks(self, user_id: int = 0,
                             illust_filter: typing.Optional[typing.Callable[[Illust], bool]] = None,
                             max_item: int = 2 ** 31,
                             max_page: int = 2 ** 31) -> typing.List[Illust]:
        if user_id == 0:
            user_id = self._api.user_id

        async def remote_fetcher():
            logger.debug("cache not found or out of date, get user bookmarks from remote")
            content = await self._flat_page(self._api.user_bookmarks_illust, "illusts", illust_filter,
                                            max_item, max_page, user_id=user_id)
            return [Illust.parse_obj(x) for x in content]

        return await self._cache_manager.get(
            identifier=(3,),
            cache_loader=self._cache_loader_factory("other_cache", "type", "user_bookmarks", "illusts",
                                                    lambda content: [Illust.parse_obj(x) for x in content]),
            remote_fetcher=remote_fetcher,
            cache_updater=self._cache_updater_factory("other_cache", "type", "user_bookmarks", "illusts",
                                                      lambda content: [x.dict() for x in content]),
            timeout=60
        )

    async def recommended_illusts(self, illust_filter: typing.Optional[typing.Callable[[Illust], bool]] = None,
                                  max_item: int = 2 ** 31,
                                  max_page: int = 2 ** 31) -> typing.List[Illust]:
        async def remote_fetcher():
            logger.debug("cache not found or out of date, get recommended illusts from remote")
            content = await self._flat_page(self._api.illust_recommended, "illusts", illust_filter,
                                            max_item, max_page)
            return [Illust.parse_obj(x) for x in content]

        return await self._cache_manager.get(
            identifier=(4,),
            cache_loader=self._cache_loader_factory("other_cache", "type", "recommended_illusts", "illusts",
                                                    lambda content: [Illust.parse_obj(x) for x in content]),
            remote_fetcher=remote_fetcher,
            cache_updater=self._cache_updater_factory("other_cache", "type", "recommended_illusts", "illusts",
                                                      lambda content: [x.dict() for x in content]),
            timeout=3600
        )

    async def illust_ranking(self, mode: str = 'day',
                             illust_filter: typing.Optional[typing.Callable[[Illust], bool]] = None) -> typing.List[
        Illust]:
        async def remote_fetcher():
            logger.debug("cache not found or out of date, get illust ranking from remote")
            content = await self._flat_page(self._api.illust_ranking, "illusts", illust_filter, 150, 5, mode=mode)
            return [Illust.parse_obj(x) for x in content]

        return await self._cache_manager.get(
            identifier=(5,),
            cache_loader=self._cache_loader_factory("illust_ranking_cache", "mode", mode, "illusts",
                                                    lambda content: [Illust.parse_obj(x) for x in content]),
            remote_fetcher=remote_fetcher,
            cache_updater=self._cache_updater_factory("illust_ranking_cache", "mode", mode, "illusts",
                                                      lambda content: [x.dict() for x in content]),
            timeout=3600
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
            timeout=60
        )

    async def download(self, illust_id: int,
                       url: str) -> bytes:
        async def remote_fetcher():
            logger.debug("cache not found or out of date, download from remote")
            with BytesIO() as bio:
                await self._api.download(url, fname=bio)
                content = bio.getvalue()

                loop = asyncio.get_running_loop()
                task = loop.run_in_executor(self._compress_executor, functools.partial(self._compress, content))
                return await task

        return await self._cache_manager.get(
            identifier=(7, illust_id),
            cache_loader=self._cache_loader_factory("download_cache", "illust_id", illust_id, "content", None),
            remote_fetcher=remote_fetcher,
            cache_updater=self._cache_updater_factory("download_cache", "illust_id", illust_id, "content",
                                                      lambda content: bson.binary.Binary(content)),
            timeout=60
        )

    @staticmethod
    def _compress(content: bytes,
                  max_size: int = 1200,
                  quantity: float = 0.8) -> bytes:
        p = ImageFile.Parser()
        p.feed(content)
        img = p.close()

        w, h = img.size
        if w > max_size or h > max_size:
            ratio = min(max_size / w, max_size / h)
            img_cp = img.resize((int(ratio * w), int(ratio * h)), Image.ANTIALIAS)
        else:
            img_cp = img.copy()
        img_cp = img_cp.convert("RGB")

        with BytesIO() as bio:
            img_cp.save(bio, format="JPEG", optimize=True, quantity=quantity)
            return bio.getvalue()


data_source = PixivDataSource()

__all__ = ('data_source', 'PixivDataSource')
