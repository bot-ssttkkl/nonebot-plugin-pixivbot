import nonebot
from nonebot.adapters.qqguild import Adapter

nonebot.init()

driver = nonebot.get_driver()
driver.register_adapter(Adapter)

nonebot.load_plugin("nonebot_plugin_pixivbot")

if __name__ == "__main__":
    nonebot.run()
