"""抓取公开 RSS，生成网页版「AI 动态」数据。

只依赖标准库，方便在 GitHub Actions 里直接跑。任何一个源失败都不影响其它源；
全部失败时保留上一次的 news.json，避免把线上页面刷成空白。
"""

from __future__ import annotations

import json
import re
import urllib.request
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from xml.etree import ElementTree

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "frontend" / "public" / "data" / "news.json"

FEEDS = [
    ("Anthropic", "https://www.anthropic.com/news.rss"),
    ("OpenAI", "https://openai.com/news/rss.xml"),
    ("Hugging Face", "https://huggingface.co/blog/feed.xml"),
    ("Google AI", "https://blog.google/technology/ai/rss/"),
    ("机器之心", "https://www.jiqizhixin.com/rss"),
    ("Simon Willison", "https://simonwillison.net/atom/everything/"),
]

MAX_ITEMS = 45
UA = "AgentConsole/0.2 (+https://github.com/blw4712)"

TAG_RULES = [
    ("模型", ("gpt", "claude", "gemini", "llama", "qwen", "模型", "model")),
    ("Agent", ("agent", "mcp", "tool", "copilot", "cursor", "智能体")),
    ("研究", ("paper", "arxiv", "research", "benchmark", "论文", "研究")),
    ("发布", ("launch", "release", "announce", "introduc", "发布", "上线")),
]


def strip_html(text: str) -> str:
    text = re.sub(r"<[^>]+>", " ", text or "")
    text = re.sub(r"&nbsp;", " ", text)
    text = re.sub(r"&amp;", "&", text)
    text = re.sub(r"&lt;", "<", text)
    text = re.sub(r"&gt;", ">", text)
    text = re.sub(r"&#39;", "'", text)
    text = re.sub(r"&quot;", '"', text)
    return re.sub(r"\s+", " ", text).strip()


def clip(text: str, limit: int = 160) -> str:
    text = strip_html(text)
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"


def parse_date(value: str | None) -> datetime:
    if not value:
        return datetime.now(timezone.utc)
    value = value.strip()
    try:
        parsed = parsedate_to_datetime(value)
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    except (TypeError, ValueError):
        pass
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    except ValueError:
        return datetime.now(timezone.utc)


def tags_for(text: str) -> list[str]:
    low = text.lower()
    hits = [name for name, words in TAG_RULES if any(word in low for word in words)]
    return hits[:3]


def fetch(url: str) -> str:
    request = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(request, timeout=15) as response:
        return response.read().decode("utf-8", errors="ignore")


def local_name(tag: str) -> str:
    return tag.split("}")[-1].lower()


def read_feed(source: str, url: str) -> list[dict]:
    try:
        root = ElementTree.fromstring(fetch(url))
    except Exception as error:  # noqa: BLE001 - 单源失败不影响整体
        print(f"[skip] {source}: {error}")
        return []

    items = []
    for node in root.iter():
        if local_name(node.tag) not in {"item", "entry"}:
            continue
        title = link = date_text = summary = ""
        for child in node:
            name = local_name(child.tag)
            if name == "title":
                title = strip_html(child.text or "")
            elif name == "link":
                link = (child.text or "").strip() or child.get("href", "")
            elif name in {"pubdate", "published", "updated", "date"}:
                date_text = child.text or ""
            elif name in {"description", "summary", "content"}:
                summary = summary or (child.text or "")
        if not title or not link:
            continue
        published = parse_date(date_text)
        items.append(
            {
                "title": title,
                "link": link,
                "source": source,
                "published": published.astimezone(timezone.utc).isoformat(),
                "summary": clip(summary),
                "tags": tags_for(f"{title} {summary}"),
            }
        )
    print(f"[ok] {source}: {len(items)}")
    return items


def main() -> None:
    collected: list[dict] = []
    for source, url in FEEDS:
        collected.extend(read_feed(source, url))

    seen = set()
    unique = []
    for item in sorted(collected, key=lambda entry: entry["published"], reverse=True):
        if item["link"] in seen:
            continue
        seen.add(item["link"])
        unique.append(item)

    if not unique:
        print("[warn] 没有抓到任何内容，保留已有文件")
        return

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "items": unique[:MAX_ITEMS],
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"[done] {len(payload['items'])} 条 -> {OUT}")


if __name__ == "__main__":
    main()
