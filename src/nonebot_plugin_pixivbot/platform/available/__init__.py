from ..func_manager import FuncManagerFactory


def register(factory: FuncManagerFactory):
    try:
        from nonebot.adapters.onebot.v11 import Adapter
        from .onebot_v11 import available
        factory.register(Adapter.get_name(), "available", available)
    except ImportError:
        pass

    try:
        from nonebot.adapters.kaiheila import Adapter
        from .kaiheila import available
        factory.register(Adapter.get_name(), "available", available)
    except ImportError:
        pass
