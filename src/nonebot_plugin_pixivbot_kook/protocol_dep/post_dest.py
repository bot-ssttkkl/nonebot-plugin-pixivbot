from abc import ABC, abstractmethod
from typing import Optional, List

from nonebot.adapters.kaiheila import Message, Bot
from nonebot.adapters.kaiheila.event import ChannelMessageEvent, PrivateMessageEvent, Event
from nonebot_plugin_access_control.subject import extract_subjects

from nonebot_plugin_pixivbot.global_context import context
from nonebot_plugin_pixivbot.model import PostIdentifier
from nonebot_plugin_pixivbot.protocol_dep.post_dest import PostDestination as BasePostDestination, \
    PostDestinationFactory as BasePostDestinationFactory, PostDestinationFactoryManager
from nonebot_plugin_pixivbot.utils.nonebot import is_superuser


class PostDestination(BasePostDestination[str, str], ABC):
    def __init__(self, bot: Bot) -> None:
        self._bot = bot

    @property
    def bot(self) -> Bot:
        return self._bot

    @abstractmethod
    async def post(self, msg: Message):
        raise NotImplementedError()


class PrivatePostDestination(PostDestination):
    def __init__(self, bot: Bot, *,
                 user_id: str,
                 event: Optional[PrivateMessageEvent] = None):
        super().__init__(bot)
        self._user_id = user_id
        self._event = event

    @property
    def identifier(self):
        # 小心递归陷阱
        return PostIdentifier("kaiheila", self._user_id, None)

    @property
    def event(self) -> Optional[PrivateMessageEvent]:
        return self._event

    def normalized(self) -> "PrivatePostDestination":
        return PrivatePostDestination(self.bot, user_id=self.user_id)

    def extract_subjects(self) -> List[str]:
        if self.event is not None:
            return extract_subjects(self.bot, self.event)

        li = []

        if self.user_id is not None:
            li.append(f"kaiheila:{self.user_id}")
            if is_superuser(self.bot, self.user_id):
                li.append("superuser")

        li.append("kaiheila")
        li.append("all")

        return li

    async def post(self, message: Message):
        if self.event is not None:
            quote = self.event.msg_id
        else:
            quote = None
        await self.bot.send_private_msg(user_id=self.user_id, message=message, quote=quote)


class ChannelPostDestination(PostDestination):
    def __init__(self, bot: Bot, *,
                 user_id: Optional[str],
                 channel_id: str,
                 guild_id: Optional[str],
                 event: Optional[ChannelMessageEvent] = None):
        super().__init__(bot)
        self._user_id = user_id
        self.channel_id = channel_id
        self.guild_id = guild_id
        self._event = event

    @property
    def identifier(self):
        # 小心递归陷阱
        return PostIdentifier("kaiheila", self._user_id, self.channel_id)

    @property
    def event(self) -> Optional[PrivateMessageEvent]:
        return self._event

    def normalized(self) -> "ChannelPostDestination":
        return ChannelPostDestination(self.bot, user_id=self.user_id, channel_id=self.channel_id,
                                      guild_id=self.guild_id)

    def extract_subjects(self) -> List[str]:
        if self.event is not None:
            return extract_subjects(self.bot, self.event)

        li = []

        if self.user_id is not None:
            li.append(f"kaiheila:{self.user_id}")
            if is_superuser(self.bot, self.user_id):
                li.append("superuser")

        li.append(f"kaiheila:c{self.channel_id}")

        if self.guild_id is not None:
            li.append(f"kaiheila:g{self.guild_id}")

        li.append("kaiheila")
        li.append("all")

        return li

    async def post(self, message: Message):
        if self.event is not None:
            quote = self.event.msg_id
        else:
            quote = None
        await self.bot.send_channel_msg(channel_id=self.channel_id, message=message, quote=quote)


@context.register_singleton()
class PostDestinationFactory(BasePostDestinationFactory[str, str], manager=PostDestinationFactoryManager):
    adapter = "kaiheila"

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
                                          event=event)
        elif isinstance(event, PrivateMessageEvent):
            return PrivatePostDestination(bot, user_id=event.author_id,
                                          event=event)
        else:
            raise ValueError("invalid event type: " + str(type(event)))
