from abc import ABC, abstractmethod
from typing import Optional

from nonebot.adapters.kaiheila import Message, Bot
from nonebot.adapters.kaiheila.event import ChannelMessageEvent, PrivateMessageEvent, Event
from nonebot_plugin_pixivbot import context
from nonebot_plugin_pixivbot.model import PostIdentifier
from nonebot_plugin_pixivbot.protocol_dep.post_dest import PostDestination as BasePostDestination, \
    PostDestinationFactory as BasePostDestinationFactory, PostDestinationFactoryManager


class PostDestination(BasePostDestination[str, str], ABC):
    def __init__(self, bot: Bot) -> None:
        self.bot = bot

    @abstractmethod
    async def post(self, msg: Message):
        raise NotImplementedError()


class PrivatePostDestination(PostDestination):
    def __init__(self, bot: Bot,
                 *, user_id: str,
                 quote_message_id: Optional[str] = None):
        super().__init__(bot)
        self._user_id = user_id
        self.quote_message_id = quote_message_id

    @property
    def identifier(self):
        # 小心递归陷阱
        return PostIdentifier("kaiheila", self._user_id, None)

    def normalized(self) -> "PrivatePostDestination":
        return PrivatePostDestination(self.bot, user_id=self.user_id)

    async def post(self, message: Message):
        await self.bot.send_private_msg(user_id=self.user_id, message=message, quote=self.quote_message_id)


class ChannelPostDestination(PostDestination):
    def __init__(self, bot: Bot,
                 *, user_id: Optional[str] = None,
                 channel_id: str,
                 guild_id: Optional[str] = None,
                 quote_message_id: Optional[str] = None):
        super().__init__(bot)
        self._user_id = user_id
        self.channel_id = channel_id
        self.guild_id = guild_id
        self.quote_message_id = quote_message_id

    @property
    def identifier(self):
        # 小心递归陷阱
        return PostIdentifier("kaiheila", self._user_id, self.channel_id)

    def normalized(self) -> "ChannelPostDestination":
        return ChannelPostDestination(self.bot, user_id=self.user_id, channel_id=self.channel_id)

    async def post(self, message: Message):
        await self.bot.send_channel_msg(channel_id=self.channel_id, message=message, quote=self.quote_message_id)


@context.require(PostDestinationFactoryManager).register
class PostDestinationFactory(BasePostDestinationFactory[str, str]):
    @classmethod
    def adapter(cls) -> str:
        return "kaiheila"

    def build(self, bot: Bot,
              user_id: Optional[str],
              group_id: Optional[str],
              guild_id: Optional[str] = None) -> PostDestination:
        if group_id is None:
            return PrivatePostDestination(bot, user_id=user_id)
        else:
            return ChannelPostDestination(bot, user_id=user_id, channel_id=group_id)

    def from_event(self, bot: Bot, event: Event) -> PostDestination:
        if isinstance(event, ChannelMessageEvent):
            return ChannelPostDestination(bot, user_id=event.author_id,
                                          channel_id=event.target_id,
                                          guild_id=event.extra.guild_id,
                                          quote_message_id=event.msg_id)
        elif isinstance(event, PrivateMessageEvent):
            return PrivatePostDestination(bot, user_id=event.author_id,
                                          quote_message_id=event.msg_id)
        else:
            raise ValueError("invalid event type: " + str(type(event)))
