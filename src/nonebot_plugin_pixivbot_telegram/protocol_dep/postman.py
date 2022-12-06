from io import StringIO

from nonebot_plugin_pixivbot import context
from nonebot_plugin_pixivbot.enums import BlockAction
from nonebot_plugin_pixivbot.model.message import IllustMessageModel, IllustMessagesModel
from nonebot_plugin_pixivbot.protocol_dep.postman import Postman as BasePostman, PostmanManager
from .post_dest import PostDestination


@context.require(PostmanManager).register
class Postman(BasePostman[int, int]):
    @classmethod
    def adapter(cls) -> str:
        return "telegram"

    async def send_plain_text(self, message: str,
                              *, post_dest: PostDestination):
        await post_dest.bot.send_message(chat_id=post_dest.real_chat_id, text=message,
                                         reply_to_message_id=post_dest.reply_to_message_id,
                                         allow_sending_without_reply=True)

    async def send_illust(self, model: IllustMessageModel,
                          *, post_dest: PostDestination):
        with StringIO() as caption:
            if model.header:
                caption.write(model.header)
                caption.write('\n')

            if model.block_action is not None:
                if model.block_action == BlockAction.no_image:
                    caption.write(model.block_message)
                    caption.write('\n')
                elif model.block_action == BlockAction.completely_block:
                    await self.send_plain_text(model.block_message, post_dest=post_dest)
                    return
                elif model.block_action == BlockAction.no_reply:
                    return

            if model.number is not None:
                caption.write("#")
                caption.write(str(model.number))
                caption.write(" ")

            caption.write(f"「{model.title}」\n作者：{model.author}\n发布时间：{model.create_time}\n")
            caption.write(model.link)

            await post_dest.bot.send_photo(chat_id=post_dest.real_chat_id, photo=model.image,
                                           caption=caption.getvalue(),
                                           reply_to_message_id=post_dest.reply_to_message_id,
                                           allow_sending_without_reply=True)

    async def send_illusts(self, model: IllustMessagesModel,
                           *, post_dest: PostDestination):
        for x in model.flat():
            await self.send_illust(x, post_dest=post_dest)


__all__ = ("Postman",)
