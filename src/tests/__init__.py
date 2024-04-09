import pytest


class MyTest:
    @pytest.fixture(autouse=True)
    def load_pixivbot(self, nonebug_init):
        import nonebot  # 这里的导入必须在函数内

        # 加载插件
        return nonebot.load_plugins("nonebot_plugin_pixivbot")
