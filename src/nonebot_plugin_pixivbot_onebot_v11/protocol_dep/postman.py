from io import StringIO

from nonebot.adapters.onebot.v11 import Message, MessageSegment

from nonebot_plugin_pixivbot import context
from nonebot_plugin_pixivbot.context import Inject
from nonebot_plugin_pixivbot.enums import BlockAction
from nonebot_plugin_pixivbot.model.message import IllustMessageModel, IllustMessagesModel
from nonebot_plugin_pixivbot.protocol_dep.postman import Postman as BasePostman, PostmanManager
from nonebot_plugin_pixivbot_onebot_v11.config import OnebotV11Config
from nonebot_plugin_pixivbot_onebot_v11.protocol_dep.post_dest import PostDestination


@context.inject
@context.require(PostmanManager).register
class Postman(BasePostman[int, int]):
    conf: OnebotV11Config = Inject(OnebotV11Config)

    @classmethod
    def adapter(cls) -> str:
        return "onebot"

    def make_illust_msg(self, model: IllustMessageModel) -> Message:
        msg = Message()

        if model.block_action is not None:
            if model.block_action == BlockAction.no_image:
                msg.append(model.block_message)
            elif model.block_action == BlockAction.completely_block:
                msg.append(model.block_message)
                return msg
            elif model.block_action == BlockAction.no_reply:
                return msg
            else:
                raise ValueError(f"invalid block_action: {model.block_action}")

        msg.append(MessageSegment.image(model.image))

        with StringIO() as sio:
            sio.write('\n')
            if model.number is not None:
                sio.write(f"#{model.number}")
            sio.write(f"「{model.title}」\n"
                      f"作者：{model.author}\n"
                      f"发布时间：{model.create_time}\n")
            if self.conf.pixiv_onebot_with_link:
                sio.write(model.link)
            else:
                sio.write(f"Pixiv ID：{model.id}")

            msg.append(MessageSegment.text(sio.getvalue()))
        return msg

    async def send_plain_text(self, message: str,
                              *, post_dest: PostDestination):
        message = Message([MessageSegment.text(message)])
        await post_dest.post(message)

    async def send_illust(self, model: IllustMessageModel,
                          *, post_dest: PostDestination):
        message = Message()
        if model.header is not None:
            message.append(MessageSegment.text(model.header + '\n'))

        message.extend(self.make_illust_msg(model))
        await post_dest.post(message)

    async def send_illusts(self, model: IllustMessagesModel,
                           *, post_dest: PostDestination):
        if len(model.messages) == 1:
            await self.send_illust(model.flat_first(), post_dest=post_dest)
        else:
            messages = [Message([MessageSegment.text(model.header)])]
            for sub_model in model.messages:
                messages.append(self.make_illust_msg(sub_model))

            await post_dest.post(messages)


__all__ = ("Postman",)
