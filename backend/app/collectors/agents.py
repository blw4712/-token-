"""Agent 采集：Claude 自定义子代理、Trae 助手目录、插件内代理。

每个代理只取名称、简介、模型和工具名，不读取提示词正文。
"""

from __future__ import annotations

import json
from pathlib import Path

from app.collectors.common import first_paragraph, read_frontmatter
from app.config import CLAUDE_AGENTS, TRAE_ASSISTANT, TRAE_PLUGINS


def _split_list(value: str) -> list[str]:
    if not value:
        return []
    cleaned = value.strip().strip("[]")
    parts = [item.strip().strip("\"'") for item in cleaned.split(",")]
    return [part for part in parts if part]


def _markdown_agent(path: Path, platform: str, scope: str, origin: str = "") -> dict:
    meta = read_frontmatter(path)
    return {
        "name": meta.get("name") or path.stem,
        "description": meta.get("description") or first_paragraph(path),
        "platform": platform,
        "scope": scope,
        "origin": origin,
        "model": meta.get("model") or "",
        "tools": _split_list(meta.get("tools") or ""),
        "path": str(path),
    }


def _claude_agents() -> list[dict]:
    if not CLAUDE_AGENTS.is_dir():
        return []
    records = []
    for path in sorted(CLAUDE_AGENTS.glob("*.md")):
        records.append(_markdown_agent(path, "claude", "user"))
    return records


def _trae_assistant() -> list[dict]:
    """Trae 助手目录下如果有代理清单，按清单记录。"""
    if not TRAE_ASSISTANT.is_dir():
        return []

    records: list[dict] = []
    for folder in sorted(TRAE_ASSISTANT.iterdir()):
        if not folder.is_dir():
            continue
        for filename in ("agent.json", "config.json"):
            candidate = folder / filename
            if not candidate.is_file():
                continue
            try:
                data = json.loads(candidate.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            if not isinstance(data, dict):
                continue
            records.append(
                {
                    "name": data.get("name") or folder.name,
                    "description": data.get("description") or "",
                    "platform": "trae",
                    "scope": "assistant",
                    "origin": "",
                    "model": data.get("model") or "",
                    "tools": [str(item) for item in (data.get("tools") or [])],
                    "path": str(candidate),
                }
            )
            break
    return records


def _plugin_agents() -> list[dict]:
    if not TRAE_PLUGINS.is_dir():
        return []

    records: list[dict] = []
    for path in sorted(TRAE_PLUGINS.glob("*/*/*/agents/*.md")):
        version_dir = path.parents[2]
        plugin_dir = version_dir.parent
        origin = f"{plugin_dir.parent.name}:{plugin_dir.name}@{version_dir.name}"
        records.append(_markdown_agent(path, "trae", "plugin", origin))
    return records


def collect() -> list[dict]:
    records = _claude_agents() + _trae_assistant() + _plugin_agents()
    records.sort(key=lambda item: (item["platform"], item["name"].lower()))
    return records
