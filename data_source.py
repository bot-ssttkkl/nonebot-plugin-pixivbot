import typing
from datetime import datetime
from io import BytesIO

import bson
import nonebot
from nonebot import logger
from pixivpy_async import *
from pixivpy_async.error import TokenError

from .model.Illust import Illust
from .model.Result import IllustResult, PagedIllustListResult, IllustListResult

mongodb_name = ""


class PixivDataSource:
    _client: PixivClient = None
    _api: AppPixivAPI = None

    async def initialize(self):
        self._client = PixivClient(proxy="socks5://127.0.0.1:7890")
        self._api = AppPixivAPI(client=self._client.start())

    def api(self) -> AppPixivAPI:
        return self._api

    async def shutdown(self):
        await self._client.close()

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
                         illust_filter: typing.Optional[typing.Callable[[Illust], bool]] = None,
                         max_item: int = 2 ** 31,
                         max_page: int = 2 ** 31,
                         *args, **kwargs) -> IllustListResult:
        cur_page = 0
        flatten = IllustListResult(illusts=[])

        # logger.debug("loading page " + str(cur_page + 1))
        raw_result = await search_func(*args, **kwargs)
        result: PagedIllustListResult = PagedIllustListResult.parse_obj(raw_result)
        if result.error is not None:
            flatten.error = result.error
            return flatten

        while len(flatten.illusts) < max_item and cur_page < max_page:
            for x in result.illusts:
                if illust_filter is None or illust_filter(x):
                    flatten.illusts.append(x)
                    if len(flatten.illusts) >= max_item:
                        break
            else:
                next_qs = AppPixivAPI.parse_qs(next_url=result.next_url)
                if next_qs is None:
                    break
                cur_page = cur_page + 1
                # logger.debug("loading page " + str(cur_page + 1))
                raw_result = await search_func(**next_qs)
                result: PagedIllustListResult = PagedIllustListResult.parse_obj(raw_result)
                if result.error is not None:
                    flatten.error = result.error
                    return flatten

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

    @staticmethod
    def _db():
        db_conn = nonebot.require("nonebot_plugin_navicat").mongodb_client
        return db_conn[mongodb_name]

    async def search_illust(self, word: str,
                            illust_filter: typing.Optional[typing.Callable[[Illust], bool]] = None,
                            max_item: int = 2 ** 31,
                            max_page: int = 2 ** 31, **kwargs) -> IllustListResult:
        cache = await self._db().search_illust_cache.find_one({"word": word})
        if cache is not None:
            if (datetime.now() - cache["update_time"]).total_seconds() < 86400:
                return IllustListResult.parse_obj(cache)

        logger.debug("cache not found or out of date, search illust from remote")
        result = await self._flat_page(self._api.search_illust, illust_filter, max_item, max_page, word=word,
                                       **kwargs)
        if result.error is None:
            await self._db().download_cache.update_one(
                {"word": word},
                {"$set": {
                    "illusts": result.dict()["illusts"],
                    "update_time": datetime.now()
                }},
                upsert=True
            )
        return result

    async def illust_detail(self, illust_id) -> IllustResult:
        cache = await self._db().illust_detail_cache.find_one({"illust_id": illust_id})
        if cache is not None:
            return IllustResult.parse_obj(cache)

        logger.debug("cache not found or out of date, get illust detail from remote")
        raw_result = await self._api.illust_detail(illust_id)
        result = IllustResult.parse_obj(raw_result)
        if result.error is None:
            await self._db().download_cache.update_one(
                {"illust_id": illust_id},
                {"$set": {
                    "illust": result.dict()["illust"],
                    "update_time": datetime.now()
                }},
                upsert=True
            )
        return result

    async def download(self, illust_id, url) -> bytes:
        cache = await self._db().download_cache.find_one({"illust_id": illust_id})
        if cache is not None:
            return cache["content"]

        logger.debug("cache not found or out of date, download from remote")
        with BytesIO() as bio:
            await self._api.download(url, fname=bio)
            content = bio.getvalue()
            await self._db().download_cache.update_one(
                {"illust_id": illust_id},
                {"$set": {
                    "content": bson.binary.Binary(bio.getvalue()),
                    "update_time": datetime.now()
                }},
                upsert=True
            )
        return content


data_source = PixivDataSource()

__all__ = ('data_source', 'PixivDataSource')
