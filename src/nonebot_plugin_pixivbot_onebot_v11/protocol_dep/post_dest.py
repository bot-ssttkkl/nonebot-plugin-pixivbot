import dataclasses
from typing import Optional, Sequence, Union, List

from nonebot import logger
from nonebot.adapters.onebot.v11 import Bot, Message, MessageSegment, MessageEvent
from nonebot_plugin_access_control.subject import extract_subjects

from nonebot_plugin_pixivbot.global_context import context
from nonebot_plugin_pixivbot.model import PostIdentifier
from nonebot_plugin_pixivbot.protocol_dep.post_dest import PostDestination as BasePostDestination, \
    PostDestinationFactory as BasePostDestinationFactory, PostDestinationFactoryManager
from nonebot_plugin_pixivbot.utils.nonebot import is_superuser


class PostDestination(BasePostDestination[int, int]):
    def __init__(self, bot: Bot,
                 user_id: Optional[int] = None,
                 group_id: Optional[int] = None,
                 event: Optional[MessageEvent] = None):
        self._bot = bot
        self._identifier = PostIdentifier("onebot", user_id, group_id)
        self._event = event

    @property
    def bot(self) -> Bot:
        return self._bot

    @property
    def identifier(self):
        return self._identifier

    @property
    def event(self) -> Optional[MessageEvent]:
        return self._event

    def normalized(self) -> "PostDestination":
        return PostDestination(self.bot, self.user_id, self.group_id)

    def extract_subjects(self) -> List[str]:
        if self.event is not None:
            return extract_subjects(self.bot, self.event)

        li = []
        if self.user_id is not None:
            li.append(f"qq:{self.user_id}")
            li.append(f"onebot:{self.user_id}")

            if is_superuser(self.bot, self.user_id):
                li.append("superuser")

        if self.group_id is not None:
            li.append(f"qq:{self.group_id}")
            li.append(f"onebot:g{self.group_id}")
            li.append("qq:group")
            li.append("onebot:group")
        else:
            li.append("qq:private")
            li.append("onebot:private")

        li.append("qq")
        li.append("onebot")
        li.append("all")

        return li

    async def post(self, message: Union[Message, Sequence[Message]]):
        if len(message) == 0:
            logger.warning("message is empty")
        else:
            if isinstance(message[0], Message):
                if len(message) > 1:
                    await self.post_multiple(message)
                else:
                    await self.post_single(message[0])
            else:
                await self.post_single(message)

    async def post_single(self, message: Message):
        if self.event:
            message.insert(0, MessageSegment.reply(self.event.message_id))

        if self.group_id:
            await self.bot.send_group_msg(group_id=self.group_id, message=message)
        else:
            await self.bot.send_msg(user_id=self.user_id, message=message)

    async def post_multiple(self, messages: Sequence[Message]):
        if not self.group_id:
            self_info = await self.bot.get_login_info()
            nickname = self_info["nickname"]
        else:
            # 获取bot的群昵称
            self_info = await self.bot.get_group_member_info(group_id=self.group_id, user_id=int(self.bot.self_id))
            nickname = self_info["card"] or self_info["nickname"]

        # 创建转发消息
        msg_dict = []

        for msg in messages:
            msg_dict.append([dataclasses.asdict(seg) for seg in msg])

        messages = [{
            "type": "node",
            "data": {
                "name": nickname,
                "uin": self.bot.self_id,
                "content": msg
            }
        } for msg in messages]

        if not self.group_id:
            await self.bot.send_private_forward_msg(
                user_id=self.user_id,
                messages=messages
            )
        else:
            await self.bot.send_group_forward_msg(
                group_id=self.group_id,
                messages=messages
            )


@context.register_singleton()
class PostDestinationFactory(BasePostDestinationFactory[int, int, MessageEvent], manager=PostDestinationFactoryManager):
    adapter = "onebot"

    def build(self, bot: Bot, user_id: Optional[int], group_id: Optional[int]) -> PostDestination:
        return PostDestination(bot, user_id, group_id)

    def from_event(self, bot: Bot, event: MessageEvent) -> PostDestination:
        user_id = getattr(event, "user_id", None)
        group_id = getattr(event, "group_id", None)

        if not user_id and not group_id:
            raise ValueError("user_id 和 group_id 不能同时为 None")

        return PostDestination(bot, user_id, group_id, event)
