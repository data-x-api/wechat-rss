# wechat-rss：把微信公众号变成 RSS 订阅

给一份公众号名单，生成标准的 RSS 订阅源，可以放进 Feedly、Inoreader、NetNewsWire 这些阅读器。**不用扫码，不用微信读书账号，不用公众号后台**，不依赖你自己的账号，所以不会碰到 `200013` 频率限制。

一个脚本，不用装依赖，不用 Docker，不用数据库，Python 3.9 以上就能跑。

```bash
git clone https://github.com/data-x-api/wechat-rss
cd wechat-rss

# 改 feeds.txt：每行一个公众号名字或 gh_ 编号
export DATAXAPI_API_KEY=dx_...
python3 wechat_rss.py feeds.txt --out docs
```

Key 在这里[注册](https://dataxapi.com/zh/signin/?button=gh-wechat-rss)领（可免费试用，最多 333 次）。

跑完 `docs/` 里每个号一个 `.xml`，还有一份能一次导入阅读器的 `feeds.opml`。样子见 [sample/36kr.xml](sample/36kr.xml)。

## 花多少钱

每跑一次，每个号 $0.02，失败不扣费。第一次遇到公众号名字时多一次 $0.02（换编号，之后记住，不再花）。

| 名单 | 多久跑一次 | 一个月约 |
|---|---|---|
| 5 个号 | 每天 1 次 | $3 |
| 20 个号 | 每天 1 次 | $12 |
| 20 个号 | 每天 4 次 | $48 |

大多数公众号一天最多发一次，每天跑一次就够了。

## 定时更新

在自己的电脑或服务器上用 cron，每天早上 8 点更新：

```bash
0 8 * * * cd /path/to/wechat-rss && DATAXAPI_API_KEY=dx_... python3 wechat_rss.py feeds.txt --out docs --site-url https://你的网址
```

把 `docs/` 用任何静态网站发布（Nginx、Cloudflare Pages、GitHub Pages 都行），`--site-url` 写这个目录的网址，阅读器里订阅 `https://你的网址/gh_xxx.xml`。

订阅源保留每个号最近 50 篇，旧文章自动累积，不会因为这次没取到就消失。某个号这次失败时，它原来的订阅源不动。

## 一次真实运行

2026-11-05（北京时间），名单里只有一个号：

```text
$ python3 wechat_rss.py feeds.txt --out docs
36氪（gh_240fbf8b33e4）：新文章 39 篇，订阅源共 39 篇
调用 2 次，其中失败 0 次（不扣费），实际扣费 $0.0400

$ python3 wechat_rss.py feeds.txt --out docs     # 再跑一遍：编号已经记住，没有新文章
36氪（gh_240fbf8b33e4）：新文章 0 篇，订阅源共 39 篇
调用 1 次，其中失败 0 次（不扣费），实际扣费 $0.0200
```

## 说明

- 订阅源里是标题、发布时间、原文链接和摘要，点开看原文。
- 名字要完全一样；不一样时会列出相近的名字，不会猜，免得订错号。
- 这是 [DataXAPI](https://dataxapi.com/zh/) 的示例项目，不是微信或腾讯的官方项目。脚本里只有调用接口的代码，没有爬虫。用到的接口：[文章列表](https://dataxapi.com/zh/apis/wechat_mp/accounts/articles/list/)、[按名字找公众号](https://dataxapi.com/zh/apis/wechat/accounts/search/)。
- 只取公开发布的文章，供个人阅读；转载或商用请先取得原作者授权。
- 问题和建议提 issue，或写信到 support@dataxapi.com。MIT 许可证。

## English

Turn WeChat Official Accounts into RSS feeds: a list of names or `gh_` IDs in, one RSS 2.0 file per account and an OPML file out. No QR login, no WeChat Read account, no admin account, no Docker, no database. One Python 3.9+ script with no dependencies. Each account costs $0.02 a run and failed calls are free. Needs a [DataXAPI key](https://dataxapi.com/signin/?button=gh-wechat-rss) in `DATAXAPI_API_KEY`. Unofficial; public articles only.
