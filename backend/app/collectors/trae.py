"""Trae Code 事件缓存适配器。

只读解析 ``~/.trae-cn/hub_event_cache/**/*.jsonl``，取出每轮 token 用量。
事件本身没有时间字段，统一用文件修改时间兜底，并在记录里保留来源文件。
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator

from app.config import TRAE_EVENTS


def iter_event_files(root: Path = TRAE_EVENTS) -> Iterator[Path]:
    """按路径排序返回事件文件，缺失目录时返回空。"""
    if not root.exists():
        return
    yield from sorted(root.rglob("*.jsonl"))


def _to_int(value: object) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _load_payload(value: object) -> dict:
    """事件内容存在 data 字段里，可能是 JSON 字符串或对象。"""
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            return {}
        return parsed if isinstance(parsed, dict) else {}
    return value if isinstance(value, dict) else {}


def _file_timestamp(path: Path) -> str:
    moment = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
    return moment.isoformat().replace("+00:00", "Z")


def parse_file(path: Path) -> tuple[list[dict], int]:
    """解析单个事件文件，返回用量记录和坏行数量。"""
    events: list[dict] = []
    bad_lines = 0

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
            if isinstance(obj, dict):
                events.append(obj)

    # 先扫一遍辅助事件：会话归属和模型名。
    session_by_task: dict[str, str] = {}
    model_by_task: dict[str, str] = {}
    for obj in events:
        kind = obj.get("type")
        data = _load_payload(obj.get("data"))
        task_id = obj.get("task_id") or ""
        if kind == "metadata" and data.get("session_id"):
            session_by_task[task_id] = str(data["session_id"])
        elif kind == "model_config":
            model = data.get("config_name") or data.get("model_name")
            if model:
                model_by_task[task_id] = str(model)

    timestamp = _file_timestamp(path)
    merged: dict[tuple[str, int], dict] = {}
    for obj in events:
        if obj.get("type") != "token_usage":
            continue
        data = _load_payload(obj.get("data"))
        task_id = str(obj.get("task_id") or path.stem)
        seq = _to_int(obj.get("seq"))
        prompt = _to_int(data.get("prompt_tokens"))
        cache_read = _to_int(data.get("cache_read_input_tokens"))
        cache_write = _to_int(data.get("cache_creation_input_tokens"))
        # prompt_tokens 含缓存部分，扣掉后才是按原价计费的输入。
        input_tokens = max(prompt - cache_read - cache_write, 0)

        merged[(task_id, seq)] = {
            "session_id": session_by_task.get(task_id) or task_id,
            "project": "-",
            "file": str(path),
            "message_id": f"{task_id}:{seq}",
            "timestamp": timestamp,
            "model": model_by_task.get(task_id) or "unknown",
            "is_synthetic": False,
            "input_tokens": input_tokens,
            "output_tokens": _to_int(data.get("completion_tokens")),
            "cache_read_tokens": cache_read,
            "cache_write_tokens": cache_write,
            "blocks": 1,
        }

    return list(merged.values()), bad_lines
