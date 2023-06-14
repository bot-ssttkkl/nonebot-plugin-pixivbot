from contextlib import asynccontextmanager
from io import StringIO

from nonebot import get_bot, logger
from nonebot.exception import ActionFailed
from nonebot_plugin_saa import MessageFactory, Text, Image, AggregatedMessageFactory
from nonebot_plugin_session import Session
from nonebot_plugin_session.saa import get_saa_target

from ..config import Config
from ..enums import BlockAction
from ..global_context import context
from ..model.message import IllustMessageModel, IllustMessagesModel

conf = context.require(Config)


@context.register_singleton()
class Postman:

    @asynccontextmanager
    async def _feedback_on_action_failed(self, session: Session):
        try:
            yield
        except ActionFailed as e:
            logger.opt(exception=e).error("图片发送失败")

            await self.post_plain_text("图片发送失败", session)

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
                sio.write(f"Pixiv ID：{model.id}")

            msg.append(Text(sio.getvalue()))
        return msg

    async def post_plain_text(self, message: str, session: Session):
        target = get_saa_target(session)
        bot = get_bot(session.bot_id)
        msg = MessageFactory(Text(message))
        await msg.send_to(target, bot)

    async def post_illust(self, model: IllustMessageModel, session: Session):
        async with self._feedback_on_action_failed(session):
            msg = MessageFactory([])
            if model.header is not None:
                msg.append(Text(model.header + '\n'))

            msg.extend(self._make_illust_msg(model))

            target = get_saa_target(session)
            bot = get_bot(session.bot_id)
            await msg.send_to(target, bot)

    async def post_illusts(self, model: IllustMessagesModel, session: Session):
        async with self._feedback_on_action_failed(session):
            if session.bot_type == "OneBot V11" and \
                    (conf.pixiv_send_forward_message == 'never' or
                     conf.pixiv_send_forward_message == 'auto' and len(model.messages) == 1):
                for x in model.flat():
                    await self.post_illust(x, session)
            else:
                messages = []
                if model.header:
                    messages.append(MessageFactory([Text(model.header)]))
                for sub_model in model.messages:
                    messages.append(self._make_illust_msg(sub_model))

                msg = AggregatedMessageFactory(messages)
                target = get_saa_target(session)
                bot = get_bot(session.bot_id)
                await msg.send_to(target, bot)
