"""
nonebot-plugin-pixivbot-onebot-v11

@Author         : ssttkkl
@License        : MIT
@GitHub         : https://github.com/ssttkkl/nonebot-plugin-pixivbot-onebot-v11
"""

# =============== register protocol_dep ===============
from .protocol_dep.authenticator import Authenticator
from .protocol_dep.post_dest import PostDestinationFactory
from .protocol_dep.postman import Postman

# ================== register handler ==================
from .handler import *
