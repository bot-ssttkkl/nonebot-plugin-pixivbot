from nonebot import require

require("nonebot_plugin_access_control")

from nonebot_plugin_access_control.service import create_plugin_service

plugin_service = create_plugin_service("nonebot_plugin_pixivbot")

common_service = plugin_service.create_subservice("common")
illust_service = common_service.create_subservice("illust")
ranking_service = common_service.create_subservice("ranking")
more_service = common_service.create_subservice("more")
random_bookmark_service = common_service.create_subservice("random_bookmark")
random_illust_service = common_service.create_subservice("random_illust")
random_recommended_illust_service = common_service.create_subservice("random_recommended_illust")
random_related_illust_service = common_service.create_subservice("random_related_illust")
random_user_illust_service = common_service.create_subservice("random_user_illust")

illust_link_service = plugin_service.create_subservice("illust_link")

schedule_service = plugin_service.create_subservice("schedule")
receive_schedule_service = schedule_service.create_subservice("receive")
manage_schedule_service = schedule_service.create_subservice("manage")

watch_service = plugin_service.create_subservice("watch")
receive_watch_service = watch_service.create_subservice("receive")
manage_watch_service = watch_service.create_subservice("manage")

invalidate_cache_service = plugin_service.create_subservice("invalidate_cache")

bind_service = plugin_service.create_subservice("bind")

help_service = plugin_service.create_subservice("help")

r18_service = plugin_service.create_subservice("r18")
r18g_service = r18_service.create_subservice("g")
