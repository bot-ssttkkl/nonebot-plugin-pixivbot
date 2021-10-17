import typing

from nonebot.log import logger
from pixivpy_async import *

from .model.Illust import Illust
from .model.Result import IllustListResult, PagedIllustListResult

_client: PixivClient = None
_api: AppPixivAPI = None


async def initialize():
    global _client, _api
    _client = PixivClient(proxy="socks5://127.0.0.1:7890")
    _api = AppPixivAPI(client=_client.start())


def api() -> AppPixivAPI:
    return _api


async def shutdown():
    await _client.close()


async def refresh(refresh_token: str):
    # Latest app version can be found using GET /v1/application-info/android
    USER_AGENT = "PixivAndroidApp/5.0.234 (Android 11; Pixel 5)"
    REDIRECT_URI = "https://app-api.pixiv.net/web/v1/users/auth/pixiv/callback"
    LOGIN_URL = "https://app-api.pixiv.net/web/v1/login"
    AUTH_TOKEN_URL = "https://oauth.secure.pixiv.net/auth/token"
    CLIENT_ID = "MOBrBDS8blbauoSck0ZfDbtuzpyT"
    CLIENT_SECRET = "lsACyCD94FhDUtGTXi3QzcFE2uU1hqtDaKeqrdwj"

    global _client, _api

    data = {
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "grant_type": "refresh_token",
        "include_policy": "true",
        "refresh_token": refresh_token,
    }
    result = await _api.requests_(method="POST", url=AUTH_TOKEN_URL, data=data, headers={"User-Agent": USER_AGENT},
                                  auth=False)
    _api.set_auth(result.access_token, result.refresh_token)
    return result


async def flat_page(search_func: typing.Callable,
                    filter: typing.Optional[typing.Callable[[Illust], bool]],
                    max_item: int = 2 ** 31,
                    max_page: int = 2 ** 31,
                    *args, **kwargs) -> IllustListResult:
    cur_page = 0
    ans = IllustListResult(illusts=[])

    logger.debug("Fetching page " + str(cur_page + 1))
    raw_result = await search_func(*args, **kwargs)
    result: PagedIllustListResult = PagedIllustListResult.parse_obj(raw_result)
    if result.error is not None:
        ans.error = result.error
        return ans

    while len(ans.illusts) < max_item and cur_page < max_page:
        for x in result.illusts:
            if filter is None or filter(x):
                ans.illusts.append(x)
                if len(ans.illusts) >= max_item:
                    break
        else:
            next_qs = api().parse_qs(next_url=result.next_url)
            if next_qs is None:
                break
            cur_page = cur_page + 1
            logger.debug("Fetching page " + str(cur_page + 1))
            raw_result = await search_func(**next_qs)
            result: PagedIllustListResult = PagedIllustListResult.parse_obj(raw_result)
            if result.error is not None:
                ans.error = result.error
                return ans

    return ans


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
