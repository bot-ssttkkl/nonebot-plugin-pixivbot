
from asyncio import create_task, TimeoutError
import dataclasses
from io import BytesIO
import typing

from nonebot.adapters.onebot.v11 import Bot, Event, Message, MessageSegment
from nonebot.adapters.onebot.v11.event import MessageEvent
from nonebot.log import logger
from nonebot.matcher import Matcher
from nonebot.typing import T_State

from .config import Config
from .data_source import PixivDataSource
from .global_context import global_context as context
from .model import Illust
from .errors import BadRequestError, QueryError


@context.register_singleton()
class Postman:
    conf = context.require(Config)
    data_source = context.require(PixivDataSource)

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
        elif group_id:
            await bot.send_group_msg(group_id=group_id, message=msg)
        else:
            await bot.send_msg(user_id=user_id, message=msg)

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

    async def send_illusts(self, illusts: typing.Union[Illust, typing.Iterable[Illust]],
                           header: typing.Union[str,
                                                MessageSegment, None] = None,
                           number: typing.Optional[int] = None,
                           *,  bot: Bot,
                           event: MessageEvent = None,
                           user_id: typing.Optional[int] = None,
                           group_id: typing.Optional[int] = None):
        if isinstance(illusts, Illust):
            await self.send_illust(illusts, header, number, bot=bot, event=event, user_id=user_id, group_id=group_id)
        elif len(illusts) == 1:
            await self.send_illust(illusts[0], header, number, bot=bot, event=event, user_id=user_id, group_id=group_id)
        else:
            msg_fut = [create_task(self.make_illust_msg(illust, number + i if number is not None else None))
                       for i, illust in enumerate(illusts)]

            if event is not None:
                if "group_id" in event.__fields__ and event.group_id:
                    group_id = event.group_id
                if "user_id" in event.__fields__ and event.user_id:
                    user_id = event.user_id

            if group_id:  # 以合并转发形式发送
                # 获取bot的群昵称
                self_info = await bot.get_group_member_info(group_id=group_id, user_id=bot.self_id)
                if self_info["card"]:
                    nickname = self_info["card"]
                else:
                    nickname = self_info["nickname"]

                # 创建转发消息
                messages = []

                if header is not None:
                    if isinstance(header, str):
                        header = MessageSegment.text(header)
                    messages.append([dataclasses.asdict(header)])

                for fut in msg_fut:
                    msg = await fut
                    messages.append([dataclasses.asdict(seg) for seg in msg])

                messages = [{
                    "type": "node",
                    "data": {
                            "name": nickname,
                            "uin": bot.self_id,
                            "content": msg
                    }
                } for msg in messages]

                await bot.send_group_forward_msg(
                    group_id=group_id,
                    messages=messages
                )
            else:
                if header:
                    await self.send_message(header, bot=bot, user_id=user_id)
                for fut in msg_fut:
                    await self.send_message(await fut, bot=bot, user_id=user_id)

    def catch_error(self, wrapped):
        async def func(bot: Bot, event: Event, state: T_State, matcher: Matcher):
            try:
                await wrapped(bot, event, state, matcher)
            except TimeoutError:
                logger.warning("Timeout")
                await self.send_message(f"下载超时", bot=bot, event=event)
            except BadRequestError as e:
                await self.send_message(str(e), bot=bot, event=event)
            except QueryError as e:
                await self.send_message(str(e), bot=bot, event=event)
            except Exception as e:
                logger.exception(e)
                await self.send_message(f"内部错误：{type(e)}{e}", bot=bot, event=event)
        return func


__all__ = ("Postman", )
