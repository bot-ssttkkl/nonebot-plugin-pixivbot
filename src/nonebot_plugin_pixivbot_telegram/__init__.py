"""
nonebot-plugin-pixivbot-telegram

@Author         : ssttkkl
@License        : MIT
@GitHub         : https://github.com/ssttkkl/nonebot-plugin-pixivbot-telegram
"""

# =============== register protocol_dep ===============
from .protocol_dep.authenticator import Authenticator
from .protocol_dep.post_dest import PostDestinationFactory
from .protocol_dep.postman import Postman
