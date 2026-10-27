"""Claude Code 会话日志适配器。

只读解析 ``~/.claude/projects/**/*.jsonl``，把每条 assistant 回复转成统一的用量记录。
记录里不保留消息正文，也不读取任何密钥。
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Iterator

from app.config import CLAUDE_PROJECTS

# 客户端自己生成的消息，不对应任何模型调用。
SYNTHETIC_MODELS = {"<synthetic>"}

TOKEN_FIELDS = (
    "input_tokens",
    "output_tokens",
    "cache_read_tokens",
    "cache_write_tokens",
)


def iter_session_files(root: Path = CLAUDE_PROJECTS) -> Iterator[Path]:
    """按路径排序返回会话日志文件，缺失目录时返回空。"""
    if not root.exists():
        return
    yield from sorted(root.rglob("*.jsonl"))


def _to_int(value: object) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def parse_file(path: Path) -> tuple[list[dict], int]:
    """解析单个会话文件，返回用量记录和坏行数量。"""
    records: list[dict] = []
    bad_lines = 0
    fallback_session = path.stem
    project = path.parent.name

    with path.open("r", encoding="utf-8", errors="replace") as fh:
        for raw in fh:
            raw = raw.strip()
            if not raw:
                continue
            try:
                obj = json.loads(raw)
            except json.JSONDecodeError:
                bad_lines += 1
                continue
            if not isinstance(obj, dict) or obj.get("type") != "assistant":
                continue

            message = obj.get("message") or {}
            usage = message.get("usage") or {}
            model = message.get("model") or "unknown"

            records.append(
                {
                    "session_id": obj.get("sessionId") or fallback_session,
                    "project": project,
                    "file": str(path),
                    "message_id": message.get("id"),
                    "timestamp": obj.get("timestamp"),
                    "model": model,
                    "is_synthetic": model in SYNTHETIC_MODELS,
                    "input_tokens": _to_int(usage.get("input_tokens")),
                    "output_tokens": _to_int(usage.get("output_tokens")),
                    "cache_read_tokens": _to_int(
                        usage.get("cache_read_input_tokens")
                    ),
                    "cache_write_tokens": _to_int(
                        usage.get("cache_creation_input_tokens")
                    ),
                    "blocks": 1,
                }
            )

    return records, bad_lines


def merge_records(records: list[dict]) -> list[dict]:
    """把同一条模型回复的多条日志合并成一条。

    客户端按内容块流式落盘，thinking、text、tool_use 各占一行，同一
    message_id 因此出现多次。前面的行是未完成快照，只有输入 token；
    最后一行才带完整的输出 token 和缓存用量。所以取输出 token 最大的
    那条，输出相同时取较晚的一条。
    """
    merged: dict[tuple[str, str], dict] = {}
    ordered: list[tuple[str, str]] = []
    anonymous: list[dict] = []

    for record in records:
        message_id = record.get("message_id")
        if not message_id:
            anonymous.append(record)
            continue

        key = (record["session_id"], message_id)
        if key not in merged:
            merged[key] = dict(record)
            ordered.append(key)
            continue

        target = merged[key]
        blocks = target["blocks"] + 1
        is_better = record["output_tokens"] > target["output_tokens"] or (
            record["output_tokens"] == target["output_tokens"]
            and (record.get("timestamp") or "") >= (target.get("timestamp") or "")
        )
        if is_better:
            merged[key] = dict(record)
        merged[key]["blocks"] = blocks

    return [merged[key] for key in ordered] + anonymous


def collect(root: Path = CLAUDE_PROJECTS) -> list[dict]:
    """采集全部会话的用量记录，已按模型回复合并。"""
    records: list[dict] = []
    for path in iter_session_files(root):
        rows, _ = parse_file(path)
        records.extend(rows)
    return merge_records(records)
