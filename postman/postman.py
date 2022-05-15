
from io import BytesIO
import typing

from nonebot.adapters.onebot.v11 import Bot, Message, MessageSegment
from nonebot.adapters.onebot.v11.event import MessageEvent

from ..model import Illust
from ..config import Config
from ..data_source import PixivDataSource
from .abstract_postman import AbstractPostman
from .pkg_context import context


@context.export_singleton()
class Postman(AbstractPostman):
    conf = context.require(Config)
    data_source = context.require(PixivDataSource)

    def __init__(self):
        super().__init__()

    async def make_illust_msg(self, illust: Illust,
                              number: typing.Optional[int] = None) -> Message:
        msg = Message()

        if illust.has_tags(self.conf.pixiv_block_tags):
            if self.conf.pixiv_block_action == "no_image":
                msg.append("该画像因含有不可描述的tag而被自主规制\n")
            elif self.conf.pixiv_block_action == "completely_block":
                return Message(MessageSegment.text("该画像因含有不可描述的tag而被自主规制"))
            elif self.conf.pixiv_block_action == "no_reply":
                return Message()
        else:
            with BytesIO() as bio:
                bio.write(await self.data_source.image(illust))
                msg.append(MessageSegment.image(bio))

        if number is not None:
            msg.append(f"#{number}")
        msg.append(f"「{illust.title}」\n"
                   f"作者：{illust.user.name}\n"
                   f"发布时间：{illust.create_date.strftime('%Y-%m-%d %H:%M:%S')}\n"
                   f"https://www.pixiv.net/artworks/{illust.id}")
        return msg

    async def send_message(self, msg: typing.Union[str, Message],
                           *,  bot: Bot,
                           event: MessageEvent = None,
                           user_id: typing.Optional[int] = None,
                           group_id: typing.Optional[int] = None):
        if event is not None:
            if isinstance(event, MessageEvent):
                if isinstance(msg, Message):
                    msg = Message(
                        [MessageSegment.reply(event.message_id), *msg])
                else:
                    msg = Message([MessageSegment.reply(
                        event.message_id), MessageSegment.text(msg)])
            await bot.send(event, msg)
        else:
            await bot.send_msg(user_id=user_id, group_id=group_id, message=msg)

    async def send_illust(self, illust: Illust,
                          header: typing.Union[str,
                                               MessageSegment, None] = None,
                          number: typing.Optional[int] = None,
                          *,  bot: Bot,
                          event: MessageEvent = None,
                          user_id: typing.Optional[int] = None,
                          group_id: typing.Optional[int] = None):
        msg = Message()
        if header is not None:
            if header is str:
                msg.append(MessageSegment.text(header))
            else:
                msg.append(header)

        msg.extend(await self.make_illust_msg(illust, number))
        await self.send_message(msg, bot=bot, event=event, user_id=user_id, group_id=group_id)

    async def send_illusts(self, illusts: typing.Iterable[Illust],
                           header: typing.Union[str,
                                                MessageSegment, None] = None,
                           number: typing.Optional[int] = None,
                           *,  bot: Bot,
                           event: MessageEvent = None,
                           user_id: typing.Optional[int] = None,
                           group_id: typing.Optional[int] = None):
        for i, illust in enumerate(illusts):
            await self.send_illust(illust, header, number + i if number is not None else None,
                                   bot=bot, event=event, user_id=user_id, group_id=group_id)
