#!/usr/bin/env python3
"""把微信公众号变成 RSS 订阅源。不用扫码，不用微信读书账号，不用公众号后台。

    python3 wechat_rss.py feeds.txt --out docs

feeds.txt 每行一个公众号名字或 gh_ 编号。每跑一次，每个号调用一次（$0.02）。
Python 3.9+，只用标准库。Key 放在环境变量 DATAXAPI_API_KEY。
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from decimal import Decimal
from email.utils import format_datetime
from html import escape as html
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from xml.sax.saxutils import escape, quoteattr

API = "https://api.dataxapi.com/v1/"
SOURCE = "gh-wechat-rss"
SIGN_UP = f"https://dataxapi.com/zh/signin/?button={SOURCE}"
KEEP = 50  # 每个订阅源保留最近多少篇


class ApiError(Exception):
    pass


class Api:
    def __init__(self, key: str):
        self.key, self.calls, self.failed, self.charged = key, 0, 0, Decimal(0)

    def call(self, capability: str, **params) -> dict:
        request = Request(
            API + capability.replace(".", "/") + "?" + urlencode(params),
            headers={"Authorization": f"Bearer {self.key}", "X-Source": SOURCE, "User-Agent": SOURCE},
        )
        for last in (False, True):
            self.calls += 1
            try:
                with urlopen(request, timeout=120) as response:
                    body = json.load(response)
                self.charged += Decimal(str(body.get("meta", {}).get("billing", {}).get("amount") or 0))
                return body
            except HTTPError as error:
                self.failed += 1
                if not last and error.code in (429, 500, 502, 503, 504):
                    time.sleep(3)  # 失败不扣费，重试一次
                    continue
                try:
                    message = json.load(error).get("message_zh")
                except ValueError:
                    message = None
                raise ApiError(message or f"HTTP {error.code}") from error
            except OSError as error:
                self.failed += 1
                raise ApiError(f"连不上接口：{error}") from error
        raise AssertionError


def resolve(api: Api, wanted: str, known: dict) -> dict:
    """名字换成原始编号，记下来，下次不再花这一次钱。名字不完全一样时不猜。"""
    if wanted in known:
        return known[wanted]
    if wanted.startswith("gh_"):
        known[wanted] = {"id": wanted, "name": wanted}
        return known[wanted]
    items = api.call("wechat.accounts.search", query=wanted)["data"]["items"]
    for item in items:
        if item.get("name") == wanted:
            known[wanted] = {"id": item["id"], "name": wanted}
            return known[wanted]
    near = "、".join(str(i.get("name")) for i in items[:5]) or "没有"
    raise ApiError(f"没有名字完全是“{wanted}”的公众号。相近的：{near}")


def rss(account: dict, items: list[dict], site: str) -> str:
    link = f"{site}/{account['id']}.xml" if site else "https://mp.weixin.qq.com/"
    entries = []
    for item in items:
        published = ""
        if item.get("published_at"):
            moment = datetime.fromisoformat(item["published_at"].replace("Z", "+00:00"))
            published = f"\n      <pubDate>{format_datetime(moment.astimezone(timezone.utc), usegmt=True)}</pubDate>"
        entries.append(
            "    <item>\n"
            f"      <title>{escape(item.get('title') or '无标题')}</title>\n"
            f"      <link>{escape(item.get('url') or '')}</link>\n"
            f"      <guid isPermaLink=\"false\">{escape(str(item.get('id') or item.get('url')))}</guid>"
            f"{published}\n"
            f"      <description>{escape(item.get('text') or '')}</description>\n"
            "    </item>"
        )
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n<rss version="2.0">\n  <channel>\n'
        f"    <title>{escape(account['name'])}</title>\n"
        f"    <link>{escape(link)}</link>\n"
        f"    <description>{escape(account['name'])} 的公众号文章</description>\n"
        + "\n".join(entries)
        + "\n  </channel>\n</rss>\n"
    )


def opml(accounts: list[dict], site: str) -> str:
    prefix = f"{site}/" if site else ""
    lines = [f'    <outline type="rss" text={quoteattr(a["name"])} xmlUrl={quoteattr(prefix + a["id"] + ".xml")}/>' for a in accounts]
    return '<?xml version="1.0" encoding="UTF-8"?>\n<opml version="2.0">\n  <head><title>公众号订阅</title></head>\n  <body>\n' + "\n".join(lines) + "\n  </body>\n</opml>\n"


def index_page(accounts: list[dict]) -> str:
    links = "\n".join(f'<li><a href="{html(a["id"])}.xml">{html(a["name"])}</a></li>' for a in accounts)
    return f'<!doctype html><meta charset="utf-8"><title>公众号订阅</title>\n<h1>公众号订阅</h1>\n<ul>\n{links}\n</ul>\n<p><a href="feeds.opml">全部（OPML）</a></p>\n'


def main() -> int:
    parser = argparse.ArgumentParser(description="把微信公众号变成 RSS 订阅源")
    parser.add_argument("feeds", type=Path, help="每行一个公众号名字或 gh_ 编号的文件，# 开头的行不算")
    parser.add_argument("--out", type=Path, default=Path("docs"), help="输出目录（默认 docs）")
    parser.add_argument("--site-url", default="", help="这个目录的网址，写进 OPML，如 https://you.github.io/wechat-rss")
    args = parser.parse_args()

    wanted = [line.strip() for line in args.feeds.read_text(encoding="utf-8").splitlines() if line.strip() and not line.startswith("#")]
    if not wanted:
        print(f"{args.feeds} 里没有公众号。每行写一个名字或 gh_ 编号。", file=sys.stderr)
        return 2
    key = os.environ.get("DATAXAPI_API_KEY")
    if not key:
        print(f"这份名单每跑一次约 ${Decimal('0.02') * len(wanted):.2f}（{len(wanted)} 个号，每个 $0.02）。")
        print(f"缺 DATAXAPI_API_KEY。到这里注册领 Key，可免费试用：{SIGN_UP}", file=sys.stderr)
        return 2

    site = args.site_url.rstrip("/")
    args.out.mkdir(parents=True, exist_ok=True)
    known_file = args.out / "accounts.json"
    known = json.loads(known_file.read_text(encoding="utf-8")) if known_file.exists() else {}
    api, accounts, failed = Api(key), [], False
    for name in wanted:
        try:
            account = resolve(api, name, known)
            accounts.append(account)
            store = args.out / f"{account['id']}.json"
            saved = json.loads(store.read_text(encoding="utf-8")) if store.exists() else []
            answer = api.call("wechat_mp.accounts.articles.list", id=account["id"])
            seen, merged, new = set(), [], 0
            # 同一篇文章每次返回的链接可能不同，认文章编号。
            before = {item.get("id") or item.get("url") for item in saved}
            for item in answer["data"]["items"] + saved:  # 新的在前；同一篇只留一次
                mark = item.get("id") or item.get("url")
                if mark in seen:
                    continue
                seen.add(mark)
                merged.append(item)
                new += mark not in before
            merged.sort(key=lambda item: item.get("published_at") or "", reverse=True)
            merged = merged[:KEEP]
            store.write_text(json.dumps(merged, ensure_ascii=False, indent=1), encoding="utf-8")
            (args.out / f"{account['id']}.xml").write_text(rss(account, merged, site), encoding="utf-8")
            print(f"{account['name']}（{account['id']}）：新文章 {new} 篇，订阅源共 {len(merged)} 篇")
        except ApiError as error:
            print(f"{name}：{error}", file=sys.stderr)  # 这个号的旧订阅源不动
            failed = True
    known_file.write_text(json.dumps(known, ensure_ascii=False, indent=1), encoding="utf-8")
    (args.out / "feeds.opml").write_text(opml(accounts, site), encoding="utf-8")
    (args.out / "index.html").write_text(index_page(accounts), encoding="utf-8")
    print(f"调用 {api.calls} 次，其中失败 {api.failed} 次（不扣费），实际扣费 ${api.charged:.4f}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
