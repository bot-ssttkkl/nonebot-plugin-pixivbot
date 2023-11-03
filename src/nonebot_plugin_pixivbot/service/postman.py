from contextlib import asynccontextmanager
from io import StringIO
from typing import Optional, Union

from nonebot import get_bot
from nonebot.exception import ActionFailed
from nonebot.internal.adapter import Event
from nonebot_plugin_saa import MessageFactory, Text, Image, AggregatedMessageFactory
from nonebot_plugin_session import Session
from nonebot_plugin_session_saa import get_saa_target

from ..config import Config
from ..enums import BlockAction
from ..global_context import context
from ..model.message import IllustMessageModel, IllustMessagesModel
from ..utils.errors import PostIllustError

conf = context.require(Config)


@context.register_singleton()
class Postman:

    @asynccontextmanager
    async def _feedback_on_action_failed(self):
        try:
            yield
        except ActionFailed as e:
            raise PostIllustError() from e

    def _make_illust_msg(self, model: IllustMessageModel) -> MessageFactory:
        msg = MessageFactory([])

        if model.block_action is not None:
            if model.block_action == BlockAction.no_image:
                msg.append(Text(model.block_message))
            elif model.block_action == BlockAction.completely_block:
                msg.append(Text(model.block_message))
                return msg
            elif model.block_action == BlockAction.no_reply:
                return msg
            else:
                raise ValueError(f"invalid block_action: {model.block_action}")

        msg.append(Image(model.image))

        with StringIO() as sio:
            sio.write('\n')
            if model.number is not None:
                sio.write(f"#{model.number}")

            sio.write(f"「{model.title}」")
            if model.total != 1:
                sio.write(f"（{model.page + 1}/{model.total}）")
            sio.write("\n")

            sio.write(f"作者：{model.author}\n"
                      f"发布时间：{model.create_time}\n")
            if conf.pixiv_send_illust_link:
                sio.write(model.link)
            else:
                sio.write(f"P站ID：{model.id}")

            msg.append(Text(sio.getvalue()))
        return msg

    async def _post(self, msg: Union[MessageFactory, AggregatedMessageFactory],
                    session: Session, event: Optional[Event] = None):
        bot = get_bot(session.bot_id)
        if event is not None:
            # QQ频道里，msg.send_to会视为推送消息，深夜发不出去
            if isinstance(msg, MessageFactory):
                await msg.send(reply=True)
            else:
                await msg.send()
        else:
            target = get_saa_target(session)
            await msg.send_to(target, bot)

    async def post_plain_text(self, message: str, session: Session, event: Optional[Event] = None):
        msg = MessageFactory(Text(message))
        await self._post(msg, session, event)

    async def post_illust(self, model: IllustMessageModel, session: Session, event: Optional[Event] = None):
        async with self._feedback_on_action_failed():
            msg = MessageFactory([])
            if model.header is not None:
                msg.append(Text(model.header + '\n'))

            msg.extend(self._make_illust_msg(model))

            await self._post(msg, session, event)

    async def post_illusts(self, model: IllustMessagesModel, session: Session, event: Optional[Event] = None):
        async with self._feedback_on_action_failed():
            if (session.bot_type != "OneBot V11" or
                    conf.pixiv_send_forward_message == 'never' or
                    conf.pixiv_send_forward_message == 'auto' and len(model.messages) == 1):
                for x in model.flat():
                    await self.post_illust(x, session, event)
            else:
                messages = []
                if model.header:
                    messages.append(MessageFactory([Text(model.header)]))
                for sub_model in model.messages:
                    messages.append(self._make_illust_msg(sub_model))

                msg = AggregatedMessageFactory(messages)
                await self._post(msg, session, event)
