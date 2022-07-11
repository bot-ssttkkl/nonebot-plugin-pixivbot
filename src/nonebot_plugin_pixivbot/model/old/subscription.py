# from typing import TypeVar, Generic, Sequence, Dict, Any, Optional
#
# from pydantic import validator
# from pydantic.generics import GenericModel
#
# from nonebot_plugin_pixivbot.postman import PostIdentifier
#
# UID = TypeVar("UID")
# GID = TypeVar("GID")
#
#
# class SubscriptionV1(GenericModel, Generic[UID, GID]):
#     user_id: Optional[UID]
#     group_id: Optional[GID]
#     type: str
#     kwargs: Dict[str, Any]
#     schedule: Sequence[int]
#
#     @validator("user_id")
#     def validate(cls, user_id, values, **kwargs):
#         group_id = None
#         if "group_id" in values:
#             group_id = values["group_id"]
#
#         if not user_id and not group_id:
#             raise ValueError("at least one of user_id and group_id should be not None")
#         return user_id
#
#     @property
#     def identifier(self):
#         return PostIdentifier("onebot", self.user_id, self.group_id)
