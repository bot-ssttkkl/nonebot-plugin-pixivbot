from pixivpy_async import *

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


async def get_refresh_token(refresh_token: str):
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
    return result
