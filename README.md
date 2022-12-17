<!-- markdownlint-disable MD033 MD036 MD041 -->

<p align="center">
  <a href="https://v2.nonebot.dev/"><img src="https://v2.nonebot.dev/logo.png" width="200" height="200" alt="nonebot"></a>
</p>

<div align="center">

nonebot_plugin_pixivbot
=====

_✨ PixivBot ✨_

</div>

<p align="center">
  <a href="https://raw.githubusercontent.com/ssttkkl/nonebot-plugin-pixivbot/master/LICENSE">
    <img src="https://img.shields.io/github/license/ssttkkl/nonebot-plugin-pixivbot.svg" alt="license">
  </a>
  <a href="https://pypi.python.org/pypi/nonebot-plugin-pixivbot">
    <img src="https://img.shields.io/pypi/v/nonebot-plugin-pixivbot.svg" alt="pypi">
  </a>
  <img src="https://img.shields.io/badge/python-3.9+-blue.svg" alt="python">
</p>

NoneBot插件，支持发送随机Pixiv插画、画师更新推送、定时订阅推送……

## 开始使用

适配协议：

- [Onebot V11](https://onebot.adapters.nonebot.dev/)
- [KOOK / 开黑啦](https://github.com/Tian-que/nonebot-adapter-kaiheila)
- [Telegram](https://github.com/nonebot/adapter-telegram)

没有找到需要的协议？欢迎适配。[适配指南](https://github.com/ssttkkl/nonebot-plugin-pixivbot/wiki/%E9%80%82%E9%85%8D%E6%8C%87%E5%8D%97)

开箱即用的Docker镜像：[ssttkkl/PixivBot](https://github.com/ssttkkl/PixivBot)

## 触发语句

### 普通语句

所有数字参数均支持中文数字和罗马数字。

- **看看<类型>榜<范围>**：查看pixiv榜单（<类型>可省略，<范围>应为a-b或a）
  - 示例：看看榜、看看日榜、看看榜1-5、看看月榜一
- **来<数量>张图**：从推荐插画随机抽选一张插画（<数量>可省略，下同）
  - 示例：来张图、来五张图
- **来<数量>张<关键字>图**：搜索关键字，从搜索结果随机抽选一张插画
  - 示例：来张初音ミク图、来五张初音ミク图
  - 注：默认开启关键字翻译功能。Bot会在平时的数据爬取时记录各个Tag的中文翻译。在搜索时，若关键字的日文翻译存在，则使用日文翻译代替关键字进行搜索。
- **来<数量>张<用户>老师的图**：搜索用户，从插画列表中随机抽选一张插画
  - 示例：来张Rella老师的图、来五张Rella老师的图
- **看看图<插画ID>**：查看ID对应的插画
  - 示例：看看图114514
- **来<数量>张私家车**：从书签中随机抽选一张插画（发送者需绑定Pixiv账号，或者在配置中指定默认Pixiv账号）
  - 示例：来张私家车、来五张私家车
- **还要**：重复上一次请求
- **不够色**：获取上一张插画的相关插画

### 命令语句

- **/pixivbot schedule \<type\> \<schedule\> [..args]**：为本群（本用户）订阅类型为<type>的定时推送功能，时间满足<schedule>时进行推送
    - \<type\>：可选值有ranking, random_bookmark, random_recommended_illust, random_illust, random_user_illust
    - \<schedule\>：有三种格式，*00:30\*x*为每隔30分钟进行一次推送，*12:00*为每天12:00进行一次推送，*00:10+00:30\*x*为从今天00:10开始每隔30分钟进行一次推送（开始时间若是一个过去的时间点，则从下一个开始推送的时间点进行推送）
    - [..args]：
      - \<type\>为ranking时，接受\<mode\> \<range\>
        - 示例：/pixivbot schedle ranking 12:00 day 1-10
      - \<type\>为random_bookmark时，接受\<pixiv_user_id\>（可空）
        - 示例：/pixivbot schedle random_bookmark 01:00*x
        - 示例：/pixivbot schedle random_bookmark 01:00*x 114514
      - \<type\>为random_illust时，接受\<word\>，若需要输入空格请用反斜杠`\ `
        - 示例：/pixivbot schedle random_illust 01:00*x
        - 示例：/pixivbot schedle random_illust 01:00*x ロリ
        - 示例：/pixivbot schedle random_illust 01:00*x Hatsune\ Miku
      - \<type\>为random_user_illust时，接受\<user\>
        - 示例：/pixivbot schedle random_user_illust 01:00*x 森倉円
      - \<type\>为random_recommend_illust时，不接受参数
- **/pixivbot schedule**：查看本群（本用户）的所有定时推送订阅
- **/pixivbot unschedule \<id\>**：取消本群（本用户）的指定的定时推送订阅
- **/pixivbot watch \<type\> [..args]**：为本群（本用户）订阅类型为<type>的更新推送功能
    - \<type\>：可选值有user_illusts, following_illusts
    - [..args]：
      - \<type\>为user_illusts时，接受\<user\>
        - 示例：/pixivbot watch user_illusts 森倉円
      - \<type\>为following_illusts时，接受\<pixiv_user_id\>（可空）
        - 示例：/pixivbot watch following_illusts
        - 示例：/pixivbot watch following_illusts 114514
- **/pixivbot watch**：查看本群（本用户）的所有更新推送订阅
- **/pixivbot watch fetch \<id\>**：【调试用命令】立刻手动触发一次指定的更新推送订阅
- **/pixivbot unwatch \<id\> [..args]**：取消本群（本用户）的指定的更新推送订阅
- **/pixivbot bind \<pixiv_user_id\>**：绑定Pixiv账号（用于随机书签功能）
- **/pixivbot unbind**：解绑Pixiv账号
- **/pixivbot invalidate_cache**：清除缓存（只有超级用户能够发送此命令）
- **/pixivbot**、**/pixivbot help**：查看帮助


## 环境配置

事前准备：登录pixiv账号并获取refresh_token。（参考：[@ZipFile Pixiv OAuth Flow](https://gist.github.com/ZipFile/c9ebedb224406f4f11845ab700124362)、[eggplants/get-pixivpy-token](https://github.com/eggplants/get-pixivpy-token)）

1. 参考[安装 | NoneBot](https://v2.nonebot.dev/docs/start/installation)安装NoneBot；
2. 参考[创建项目 | NoneBot](https://v2.nonebot.dev/docs/tutorial/create-project)创建一个NoneBot实例；
3. 使用`pip install nonebot-plugin-pixivbot[xxx]`安装特定适配器的插件；
4. 修改pyproject.toml，启用插件（`plugins=[..., "nonebot_plugin_pixivbot"]`）；
5. 在.env.prod中修改配置（参考下方）；

## 配置外部数据库（可选）

PixivBot需要使用数据库存放订阅以及缓存，默认使用SQLite。

### SQLite

若需要自定义SQLite数据库文件路径，请设置配置项：

- pixiv_sql_conn_url=`sqlite+aiosqlite:///<数据库文件路径>`

### PostgreSQL

若需要使用PostgreSQL，请设置配置项：

- pixiv_sql_conn_url=`postgresql+asyncpg://<用户名>:<密码>@<主机>:<端口>/<数据库名>`

并且安装`nonebot-plugin-pixivbot[postgresql]`

### MongoDB

若需要使用MongoDB，请设置配置项：
- pixiv_mongo_conn_url=`mongodb://<用户名>:<密码>@<主机>:<端口>/<用户所属的数据库>`
- pixiv_mongo_database_name=`连接的MongoDB数据库`

并且安装`nonebot-plugin-pixivbot[mongo]`

## 配置项一览

最小配置：
```
pixiv_refresh_token=  # 前面获取的REFRESH_TOKEN
```

完整配置（除最小配置出现的配置项以外都是可选项，给出的是默认值）（NoneBot配置项这里不列出，参考[配置 | NoneBot](https://v2.nonebot.dev/docs/tutorial/configuration#%E8%AF%A6%E7%BB%86%E9%85%8D%E7%BD%AE%E9%A1%B9)）：

```
superuser=[]  # 能够发送超级命令的用户（JSON数组，格式为["onebot:123456", "kaiheila:1919810"]，下同）
blocklist=[]  # Bot不响应的用户，可以避免Bot之间相互调用（JSON数组）

pixiv_data_source=  # 使用的数据库类型，可选值：sql，mongo。若未设置，则根据是否设置了pixiv_mongo_conn_url自动判断。
pixiv_sql_conn_url=sqlite+aiosqlite:///pixiv_bot.db  # SQL连接URL，仅支持SQLite与PostgreSQL（通过SQLAlchemy进行连接，必须使用异步的DBAPI）
pixiv_mongo_conn_url=  # MongoDB连接URL，格式：mongodb://<用户名>:<密码>@<主机>:<端口>/<数据库>。
pixiv_mongo_database_name=  # 连接的MongoDB数据库

pixiv_refresh_token=  # 前面获取的REFRESH_TOKEN
pixiv_proxy=None  # 代理URL，推荐使用socks5代理
pixiv_query_timeout=60  # 查询超时（单位：秒）
pixiv_loading_prompt_delayed_time=5  # 加载提示消息的延迟时间（“努力加载中”的消息会在请求发出多少秒后发出）（单位：秒）
pixiv_simultaneous_query=8  # 向Pixiv查询的并发数

# 缓存过期时间/删除时间（单位：秒）
pixiv_download_cache_expires_in=604800  # 默认值：7天
pixiv_illust_detail_cache_expires_in=604800
pixiv_user_detail_cache_expires_in=604800
pixiv_illust_ranking_cache_expires_in=21600  # 默认值：6小时
pixiv_search_illust_cache_expires_in=86400  # 默认值：1天
pixiv_search_illust_cache_delete_in=2592000  # 默认值：30天
pixiv_search_user_cache_expires_in=86400
pixiv_search_user_cache_delete_in=2592000
pixiv_user_illusts_cache_expires_in=86400
pixiv_user_illusts_cache_delete_in=2592000
pixiv_user_bookmarks_cache_expires_in=86400
pixiv_user_bookmarks_cache_delete_in=2592000
pixiv_related_illusts_cache_expires_in=86400
pixiv_other_cache_expires_in=21600

pixiv_block_tags=[]  # 当插画含有指定tag时会被过滤
pixiv_block_action=no_image  # 过滤时的动作，可选值：no_image(不显示插画，回复插画信息), completely_block(只回复过滤提示), no_reply(无回复)

pixiv_download_quantity=original  # 插画下载品质，可选值：original, square_medium, medium, large
pixiv_download_custom_domain=None  # 使用反向代理下载插画的域名

pixiv_compression_enabled=False  # 启用插画压缩
pixiv_compression_max_size=None  # 插画压缩最大尺寸
pixiv_compression_quantity=None  # 插画压缩品质（0到100）

pixiv_query_to_me_only=False  # 只响应关于Bot的查询
pixiv_command_to_me_only=False  # 只响应关于Bot的命令

pixiv_query_cooldown=0  # 每次查询的冷却时间
pixiv_no_query_cooldown_users=[]  # 在这个列表中的用户不受冷却时间的影响（JSON数组）
pixiv_max_item_per_query=10  # 每个查询最多请求的插画数量

pixiv_tag_translation_enabled=True  # 启用搜索关键字翻译功能（平时搜索时记录标签翻译，在查询时判断是否存在对应中日翻译）

pixiv_more_enabled=True  # 启用重复上一次请求（还要）功能
pixiv_query_expires_in=10*60  # 上一次请求的过期时间（单位：秒）

pixiv_illust_query_enabled=True  # 启用插画查询（看看图）功能

pixiv_ranking_query_enabled=True  # 启用榜单查询（看看榜）功能
pixiv_ranking_default_mode=day  # 默认查询的榜单，可选值：day, week, month, day_male, day_female, week_original, week_rookie, day_manga
pixiv_ranking_default_range=[1, 3]  # 默认查询的榜单范围
pixiv_ranking_fetch_item=150  # 每次从服务器获取的榜单项数（查询的榜单范围必须在这个数目内）
pixiv_ranking_max_item_per_query=5  # 每次榜单查询最多能查询多少项

pixiv_random_illust_query_enabled=True  # 启用关键字插画随机抽选（来张xx图）功能
pixiv_random_illust_method=bookmark_proportion  # 随机抽选方法，下同，可选值：bookmark_proportion(概率与书签数成正比), view_proportion(概率与阅读量成正比), timedelta_proportion(概率与投稿时间和现在的时间差成正比), uniform(相等概率)
pixiv_random_illust_min_bookmark=0  # 过滤掉书签数小于该值的插画，下同
pixiv_random_illust_min_view=0  # 过滤掉阅读量小于该值的插画，下同
pixiv_random_illust_max_page=20  # 每次从服务器获取的查询结果页数，下同
pixiv_random_illust_max_item=500  # 每次从服务器获取的查询结果项数，下同

pixiv_random_recommended_illust_query_enabled=True  # 启用推荐插画随机抽选（来张图）功能
pixiv_random_recommended_illust_method=uniform
pixiv_random_recommended_illust_min_bookmark=0
pixiv_random_recommended_illust_min_view=0
pixiv_random_recommended_illust_max_page=40
pixiv_random_recommended_illust_max_item=1000

pixiv_random_related_illust_query_enabled=True  # 启用关联插画随机抽选（不够色）功能
pixiv_random_related_illust_method=bookmark_proportion
pixiv_random_related_illust_min_bookmark=0
pixiv_random_related_illust_min_view=0
pixiv_random_related_illust_max_page=4
pixiv_random_related_illust_max_item=100

pixiv_random_user_illust_query_enabled=True  # 启用用户插画随机抽选（来张xx老师的图）功能
pixiv_random_user_illust_method=timedelta_proportion
pixiv_random_user_illust_min_bookmark=0
pixiv_random_user_illust_min_view=0
pixiv_random_user_illust_max_page=2147483647
pixiv_random_user_illust_max_item=2147483647

pixiv_random_bookmark_query_enabled=True  # 启用用户书签随机抽选（来张私家车）功能
pixiv_random_bookmark_user_id=0  # 当QQ用户未绑定Pixiv账号时，从该Pixiv账号的书签内抽选
pixiv_random_bookmark_method=uniform
pixiv_random_bookmark_min_bookmark=0
pixiv_random_bookmark_min_view=0
pixiv_random_bookmark_max_page=2147483647
pixiv_random_bookmark_max_item=2147483647

pixiv_watch_interval=7200  # 更新推送的查询间隔
```

## Special Thanks

- [Mikubill/pixivpy-async](https://github.com/Mikubill/pixivpy-async)

- [nonebot/nonebot2](https://github.com/nonebot/nonebot2)

## 在线乞讨

<details><summary>点击请我打两把maimai</summary>

![](https://github.com/ssttkkl/ssttkkl/blob/main/afdian-ssttkkl.jfif)

</details>


## LICENSE

```
MIT License

Copyright (c) 2021 ssttkkl

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

```
