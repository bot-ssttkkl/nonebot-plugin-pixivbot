import nonebot

nonebot.init()

driver = nonebot.get_driver()

nonebot.load_plugin("nonebot_plugin_pixivbot")

if __name__ == "__main__":
    nonebot.run()
