import html
import re
from urllib.parse import quote

import feedparser
import httpx

from .config import Domain
from .models import Item

UA = {"User-Agent": "intel-analyst/0.1 (+research)"}
_TAG = re.compile(r"<[^>]+>")


def _clean(s: str, n: int = 600) -> str:
    return _TAG.sub("", html.unescape(s or "")).strip()[:n]


def parse_feed(content: bytes | str, source: str, domain: str) -> list[Item]:
    feed = feedparser.parse(content)
    out = []
    for e in feed.entries:
        if not e.get("link") or not e.get("title"):
            continue
        out.append(Item(
            url=e.link, title=_clean(e.title, 300),
            summary=_clean(e.get("summary", "")), source=source,
            published=e.get("published", e.get("updated", "")), domain=domain,
        ))
    return out


def fetch_source(src: dict, domain: str, client: httpx.Client) -> list[Item]:
    if src["type"] == "rss":
        url = src["url"]
    elif src["type"] == "arxiv":
        url = ("https://export.arxiv.org/api/query?search_query=" + quote(src["query"])
               + f"&sortBy=submittedDate&sortOrder=descending&max_results={src.get('max', 20)}")
    else:
        raise ValueError(f"unknown source type: {src['type']}")
    r = client.get(url, headers=UA, timeout=30, follow_redirects=True)
    r.raise_for_status()
    return parse_feed(r.content, src["name"], domain)


def score(item: Item, d: Domain) -> float:
    text = f"{item.title} {item.summary}".lower()
    if any(x.lower() in text for x in d.exclude):
        return -1
    return sum(w * (2 if k.lower() in item.title.lower() else 1)
               for k, w in d.keywords.items() if k.lower() in text)


def collect(d: Domain, client: httpx.Client | None = None, min_score: float = 1) -> tuple[list[Item], list[str]]:
    """返回 (相关条目, 错误列表)。单个源失败不影响其它源。"""
    own = client is None
    client = client or httpx.Client()
    items, errors = [], []
    try:
        for src in d.sources:
            try:
                items += fetch_source(src, d.key, client)
            except Exception as ex:  # noqa: BLE001
                errors.append(f"{src['name']}: {ex}")
    finally:
        if own:
            client.close()
    for it in items:
        it.score = score(it, d)
    return [i for i in items if i.score >= min_score], errors
