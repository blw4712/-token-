"""Skill 采集：Claude 用户级与项目级、Trae 内置与插件。

只读目录，不执行任何技能脚本，也不读取技能正文之外的配置。
"""

from __future__ import annotations

import json
from pathlib import Path

from app.collectors.common import first_paragraph, read_frontmatter
from app.config import (
    CLAUDE_JSON,
    CLAUDE_SKILLS,
    TRAE_PLUGINS,
    TRAE_SKILL_CONFIG,
    TRAE_SKILLS,
)

SCOPE_LABEL = {
    "global": "用户级",
    "project": "项目级",
    "builtin": "内置",
    "plugin": "插件",
}


def _skill_record(
    folder: Path,
    platform: str,
    scope: str,
    origin: str | None = None,
) -> dict | None:
    skill_file = folder / "SKILL.md"
    if not skill_file.is_file():
        return None

    meta = read_frontmatter(skill_file)
    name = meta.get("name") or folder.name
    description = meta.get("description") or first_paragraph(skill_file)
    return {
        "name": name,
        "description": description,
        "platform": platform,
        "scope": scope,
        "scope_label": SCOPE_LABEL.get(scope, scope),
        "origin": origin or "",
        "path": str(folder),
        "enabled": True,
    }


def _load_skill_config() -> dict:
    try:
        return json.loads(TRAE_SKILL_CONFIG.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def _apply_trae_status(records: list[dict]) -> None:
    config = _load_skill_config()
    disabled = set(config.get("disabledSkills") or [])
    builtin_status = config.get("builtinSkillStatus") or {}
    deleted = set(config.get("deletedSkills") or [])

    for record in records:
        if record["platform"] != "trae":
            continue
        name = record["name"]
        if name in deleted:
            record["enabled"] = False
        elif name in disabled:
            record["enabled"] = False
        elif name in builtin_status:
            record["enabled"] = bool(builtin_status[name])


def _claude_project_roots() -> list[Path]:
    try:
        data = json.loads(CLAUDE_JSON.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []

    roots: list[Path] = []
    for raw in (data.get("projects") or {}):
        path = Path(raw)
        if path.is_dir():
            roots.append(path)
    return roots


def _direct_skill_folders(root: Path) -> list[Path]:
    if not root.is_dir():
        return []
    return sorted(
        (item for item in root.iterdir() if item.is_dir()), key=lambda p: p.name.lower()
    )


def collect() -> list[dict]:
    """返回全部已安装技能，同一条记录里带平台、作用域和启用状态。"""
    records: list[dict] = []

    for folder in _direct_skill_folders(CLAUDE_SKILLS):
        record = _skill_record(folder, "claude", "global")
        if record:
            records.append(record)

    for project in _claude_project_roots():
        for folder in _direct_skill_folders(project / ".claude" / "skills"):
            record = _skill_record(folder, "claude", "project", str(project))
            if record:
                records.append(record)

    for folder in _direct_skill_folders(TRAE_SKILLS):
        if folder.name.startswith("_"):
            continue
        record = _skill_record(folder, "trae", "builtin")
        if record:
            records.append(record)

    if TRAE_PLUGINS.is_dir():
        for skill_file in sorted(TRAE_PLUGINS.glob("*/*/*/skills/*/SKILL.md")):
            folder = skill_file.parent
            version_dir = folder.parents[1]
            plugin_dir = folder.parents[2]
            registry = folder.parents[3].name
            origin = f"{registry}:{plugin_dir.name}@{version_dir.name}"
            record = _skill_record(folder, "trae", "plugin", origin)
            if record:
                records.append(record)

    for project in _claude_project_roots():
        for folder in _direct_skill_folders(project / ".trae" / "skills"):
            record = _skill_record(folder, "trae", "project", str(project))
            if record:
                records.append(record)

    _apply_trae_status(records)

    # 同一个目录可能既被当成用户级又被当成项目级，按路径去重。
    unique: list[dict] = []
    seen: set[str] = set()
    for record in records:
        key = record["path"].lower()
        if key in seen:
            continue
        seen.add(key)
        unique.append(record)

    unique.sort(key=lambda item: (item["platform"], item["scope"], item["name"].lower()))
    return unique
