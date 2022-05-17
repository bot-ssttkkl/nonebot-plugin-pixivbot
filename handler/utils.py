import functools
import typing

from nonebot.adapters.onebot.v11.event import MessageEvent


def fill_id(func):
    @functools.wraps(func)
    async def wrapper(*args, event: MessageEvent = None,
                user_id: typing.Optional[int] = None,
                group_id: typing.Optional[int] = None, **kwargs):
        if event:
            user_id = event.user_id if "user_id" in event.__fields__ else None
            group_id = event.group_id if "group_id" in event.__fields__ else None
        return await func(*args, event=event, user_id=user_id, group_id=group_id, **kwargs)
    return wrapper

    # 这样写的话APScheduler不会await：
    # 
    # def wrapper(*args, event: MessageEvent = None,
    #             user_id: typing.Optional[int] = None,
    #             group_id: typing.Optional[int] = None, **kwargs):
    #     if event:
    #         user_id = event.user_id if "user_id" in event.__fields__ else None
    #         group_id = event.group_id if "group_id" in event.__fields__ else None
    #     return func(*args, event=event, user_id=user_id, group_id=group_id, **kwargs)
    # return wrapper
