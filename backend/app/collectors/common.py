"""Markdown 文件头信息解析，供 Skill 和 Agent 采集共用。"""

from __future__ import annotations

from pathlib import Path

FOLDED = {">", ">-", ">+", "|", "|-", "|+"}


def read_frontmatter(path: Path) -> dict[str, str]:
    """读取 ``---`` 包裹的头部字段，只保留顶层键值。"""
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return {}

    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}

    fields: dict[str, str] = {}
    index = 1
    while index < len(lines):
        raw = lines[index]
        line = raw.strip()
        if line == "---":
            break
        index += 1
        if not line or line.startswith("#") or raw[:1] in (" ", "\t"):
            continue
        if ":" not in line:
            continue

        key, _, value = line.partition(":")
        key = key.strip()
        value = value.strip()
        if not key:
            continue

        if value in FOLDED:
            block: list[str] = []
            while index < len(lines):
                following = lines[index]
                if following.strip() == "---":
                    break
                if following.strip() and following[:1] not in (" ", "\t"):
                    break
                block.append(following.strip())
                index += 1
            joiner = "\n" if value.startswith("|") else " "
            fields[key] = joiner.join(part for part in block if part).strip()
        else:
            fields[key] = value.strip("\"'").strip()

    return fields


def first_paragraph(path: Path, limit: int = 160) -> str:
    """头部没有描述时，取正文第一段作为简介。"""
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""

    lines = text.splitlines()
    start = 0
    if lines and lines[0].strip() == "---":
        for index, line in enumerate(lines[1:], start=1):
            if line.strip() == "---":
                start = index + 1
                break

    paragraph: list[str] = []
    for line in lines[start:]:
        stripped = line.strip()
        if not stripped:
            if paragraph:
                break
            continue
        if stripped.startswith("#"):
            if paragraph:
                break
            continue
        paragraph.append(stripped)

    text_out = " ".join(paragraph)
    return text_out[:limit]
