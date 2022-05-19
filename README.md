nonebot_plugin_pixivbot
=====

## 环境配置

事前准备：登录pixiv账号并获取refresh_token。（参考：[@ZipFile Pixiv OAuth Flow](https://gist.github.com/ZipFile/c9ebedb224406f4f11845ab700124362)）

1. 参考[安装 | NoneBot](https://v2.nonebot.dev/guide/installation.html)安装NoneBot和OneBot V11适配器；
2. 参考[创建一个完整的项目 | NoneBot](https://v2.nonebot.dev/guide/creating-a-project.html)创建一个Bot实例；
3. 将本插件clone到插件目录；
4. 别忘了`pip install -r requirement.txt`安装依赖包；
5. 运行`nb plugin install nonebot_plugin_apscheduler`安装定时任务插件；
6. 安装MongoDB（用于保存缓存）；
7. 在.env.prod中修改配置；

## 触发语句

普通语句：

所有数字参数均支持中文数字和罗马数字。

- **看看<类型>榜<范围>***：查看pixiv榜单（<类型>可省略，<范围>应为a-b或a）
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

命令语句：

- **/pixivbot schedule \<type\> \<schedule\> [..args]**：为本群（本用户）订阅类型为<type>的定时推送功能，时间满足<schedule>时进行推送
    - \<type\>：可选值有ranking, random_bookmark, random_recommended_illust, random_illust, random_user_illust
    - \<schedule\>：有三种格式，*00:30\*x*为每隔30分钟进行一次推送，*12:00*为每天12:00进行一次推送，*00:10+00:30\*x*为从今天00:10开始每隔30分钟进行一次推送（开始时间若是一个过去的时间点，则从下一个开始推送的时间点进行推送）
    - [..args]：
      - \<type\>为ranking时，接受\<mode\> \<range\>
      - \<type\>为random_bookmark时，接受\<pixiv_user_id\>
      - \<type\>为random_illust时，接受\<word\>
      - \<type\>为random_user_illust时，接受\<user\>
- **/pixivbot schedule**：查看本群（本用户）的所有订阅
- **/pixivbot unschedule <type>**：取消本群（本用户）的订阅
- **/pixivbot bind <pixiv_user_id>**：绑定Pixiv账号（用于随机书签功能）
- **/pixivbot unbind**：解绑Pixiv账号
- **/pixivbot invalidate_cache**：清除缓存

## 注意事项

1. 必须登录pixiv账号并获取refresh_token才能使用。
2. 尽管作者已经尽力以高并发作为目标进行开发，但由于向Pixiv发送**搜索请求**太频繁会撞Rate Limit、收到警告甚至被ban号，因此不保证并发用户数量较大时还能够正常使用。（或者只开放部分功能当普通的涩图bot）
3. 根据1和2，建议使用小号登录。
4. 学业繁忙，issue可能不会及时处理。

## 配置

最小配置：
```
pixiv_refresh_token=  # 前面获取的REFRESH_TOKEN
pixiv_mongo_conn_url=  # MongoDB连接URL，格式：mongodb://<用户名>:<密码>@<主机>:<端口>/<数据库>
pixiv_mongo_database_name=  # 连接的MongoDB数据库
```

完整配置（除最小配置出现的配置项以外都是可选项，给出的是默认值）：
```
pixiv_refresh_token=  # 前面获取的REFRESH_TOKEN
pixiv_mongo_conn_url=  # MongoDB连接URL，格式：mongodb://<用户名>:<密码>@<主机>:<端口>/<数据库>
pixiv_mongo_database_name=  # 连接的MongoDB数据库
pixiv_proxy=None  # 代理URL
pixiv_query_timeout=60  # 查询超时（单位：秒）
pixiv_simultaneous_query=8  # 向Pixiv查询的并发数

# 缓存过期时间（单位：秒）
pixiv_download_cache_expires_in = 3600 * 24 * 7
pixiv_illust_detail_cache_expires_in = 3600 * 24 * 7
pixiv_user_detail_cache_expires_in = 3600 * 24 * 7
pixiv_illust_ranking_cache_expires_in = 3600 * 6
pixiv_search_illust_cache_expires_in = 3600 * 24
pixiv_search_user_cache_expires_in = 3600 * 24
pixiv_user_illusts_cache_expires_in = 3600 * 24
pixiv_user_bookmarks_cache_expires_in = 3600 * 24
pixiv_related_illusts_cache_expires_in = 3600 * 24
pixiv_other_cache_expires_in = 3600 * 6

pixiv_block_tags=[]  # 当插画含有指定tag时会被过滤
pixiv_block_action=no_image  # 过滤时的动作，可选值：no_image(不显示插画，回复插画信息), completely_block(只回复过滤提示), no_reply(无回复)

pixiv_download_quantity=original  # 插画下载品质，可选值：original, square_medium, medium, large
pixiv_download_custom_domain=None  # 使用反向代理下载插画的域名

pixiv_compression_enabled=False  # 启用插画压缩
pixiv_compression_max_size=None  # 插画压缩最大尺寸
pixiv_compression_quantity=None  # 插画压缩品质（0到100）

pixiv_more_enabled=True  # 启用重复上一次请求（还要）功能

pixiv_illust_query_enabled=True  # 启用插画查询（看看图）功能

pixiv_tag_translation_enabled=True  # 启用搜索关键字翻译功能

pixiv_query_cooldown=0  # 每次查询的冷却时间
pixiv_no_query_cooldown_users=[]  # 在这个列表中的用户不受冷却时间的影响

pixiv_ranking_query_enabled=True  # 启用榜单查询（看看榜）功能
pixiv_ranking_default_mode=day  # 默认查询的榜单，可选值：day, week, month, day_male, day_female, week_original, week_rookie, day_manga
pixiv_ranking_default_range=[1, 3]  # 默认查询的榜单范围
pixiv_ranking_fetch_item=150  # 每次从服务器获取的榜单项数（查询的榜单范围必须在这个数目内）
pixiv_ranking_max_item_per_query=5  # 每次榜单查询最多能查询多少项
pixiv_ranking_max_item_per_msg=1  # 榜单查询的回复信息每条包含多少项

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

pixiv_random_related_illust_query_enabled = True  # 启用关联插画随机抽选（不够色）功能
pixiv_random_related_illust_method = "bookmark_proportion"
pixiv_random_related_illust_min_bookmark = 0
pixiv_random_related_illust_min_view = 0
pixiv_random_related_illust_max_page = 4
pixiv_random_related_illust_max_item = 100

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

pixiv_poke_action=random_recommended_illust  # 戳一戳的功能，可选值：空, ranking, random_recommended_illust, random_bookmark
```

## Special Thanks

[Mikubill/pixivpy-async](https://github.com/Mikubill/pixivpy-async)

[nonebot/nonebot2](https://github.com/nonebot/nonebot2)


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
