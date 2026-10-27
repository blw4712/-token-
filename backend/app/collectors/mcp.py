"""MCP 采集：Trae 本地工具缓存、插件声明、Claude 项目配置。

只读取服务名和工具名，命令、参数、环境变量、地址一律不进入结果。
"""

from __future__ import annotations

import json
from pathlib import Path

from app.config import CLAUDE_JSON, TRAE_MCPS, TRAE_PLUGIN_INSTALLED


def _load_json(path: Path) -> dict | list | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def _tool_names(server_dir: Path) -> list[str]:
    tools_dir = server_dir / "tools"
    if not tools_dir.is_dir():
        return []
    names: list[str] = []
    for item in sorted(tools_dir.glob("*.json")):
        data = _load_json(item)
        if isinstance(data, dict) and data.get("name"):
            names.append(str(data["name"]))
        else:
            names.append(item.stem)
    return names


def _trae_cache() -> list[dict]:
    """扫描 ``~/.trae-cn/mcps/<工作区>/<分类>/<服务>`` 缓存。"""
    if not TRAE_MCPS.is_dir():
        return []

    records: list[dict] = []
    for metadata in sorted(TRAE_MCPS.glob("*/*/*/SERVER_METADATA.json")):
        server_dir = metadata.parent
        data = _load_json(metadata)
        name = (data or {}).get("server_name") if isinstance(data, dict) else None
        name = str(name or server_dir.name)
        records.append(
            {
                "name": name,
                "platform": "trae",
                "scope": "workspace",
                "scope_label": "Trae 工作区",
                "origin": server_dir.parents[1].name,
                "category": server_dir.parent.name,
                "workspace": server_dir.parents[1].name,
                "transport": "",
                "tools": _tool_names(server_dir),
                "enabled": True,
                "source": "trae-cache",
            }
        )
    return records


def _plugin_servers() -> list[dict]:
    """插件市场清单里声明过的 MCP 服务，只取服务名。"""
    data = _load_json(TRAE_PLUGIN_INSTALLED)
    if not isinstance(data, dict):
        return []

    records: list[dict] = []
    marketplaces = ((data.get("data") or {}).get("marketplaces")) or []
    for group in marketplaces:
        for plugin in (group or {}).get("plugins") or []:
            raw = plugin.get("mcp_servers_json") or ""
            if not raw:
                continue
            try:
                declared = json.loads(raw)
            except json.JSONDecodeError:
                continue
            names: list[str] = []
            if isinstance(declared, dict):
                names = [str(key) for key in declared]
            elif isinstance(declared, list):
                for item in declared:
                    if isinstance(item, dict) and item.get("name"):
                        names.append(str(item["name"]))
            for name in names:
                records.append(
                    {
                        "name": name,
                        "platform": "trae",
                        "scope": "plugin",
                        "scope_label": "插件",
                        "origin": plugin.get("plugin_id") or "",
                        "category": "",
                        "workspace": "",
                        "transport": "",
                        "tools": [],
                        "enabled": True,
                        "source": "plugin",
                    }
                )
    return records


def _claude_projects() -> list[dict]:
    data = _load_json(CLAUDE_JSON)
    if not isinstance(data, dict):
        return []

    records: list[dict] = []
    for project_path, project in (data.get("projects") or {}).items():
        if not isinstance(project, dict):
            continue
        disabled = set(project.get("disabledMcpjsonServers") or [])
        for name, config in (project.get("mcpServers") or {}).items():
            config = config if isinstance(config, dict) else {}
            transport = config.get("type") or ("stdio" if config.get("command") else "")
            records.append(
                {
                    "name": str(name),
                    "platform": "claude",
                    "scope": "project",
                    "scope_label": "项目级",
                    "origin": str(project_path),
                    "category": "",
                    "workspace": "",
                    "transport": str(transport),
                    "tools": [],
                    "enabled": str(name) not in disabled,
                    "source": "claude-project",
                }
            )

        mcp_file = Path(project_path) / ".mcp.json"
        if not mcp_file.is_file():
            continue
        declared = _load_json(mcp_file)
        if not isinstance(declared, dict):
            continue
        for name, config in (declared.get("mcpServers") or {}).items():
            config = config if isinstance(config, dict) else {}
            transport = config.get("type") or ("stdio" if config.get("command") else "")
            records.append(
                {
                    "name": str(name),
                    "platform": "claude",
                    "scope": "project",
                    "scope_label": "项目级",
                    "origin": str(project_path),
                    "category": "",
                    "workspace": "",
                    "transport": str(transport),
                    "tools": [],
                    "enabled": str(name) not in disabled,
                    "source": "mcp-file",
                }
            )
    return records


def collect() -> list[dict]:
    """按服务名合并，同一个服务在多个工作区只出现一次。"""
    groups: dict[tuple[str, str], dict] = {}
    for record in _trae_cache() + _plugin_servers() + _claude_projects():
        key = (record["platform"], record["name"])
        target = groups.get(key)
        if target is None:
            groups[key] = record
            groups[key]["instances"] = [
                {
                    "scope_label": record["scope_label"],
                    "origin": record["origin"],
                    "workspace": record["workspace"],
                    "category": record["category"],
                }
            ]
            continue

        target["enabled"] = target["enabled"] or record["enabled"]
        target["tools"] = sorted(set(target["tools"]) | set(record["tools"]))
        if not target.get("transport"):
            target["transport"] = record.get("transport") or ""
        target["instances"].append(
            {
                "scope_label": record["scope_label"],
                "origin": record["origin"],
                "workspace": record["workspace"],
                "category": record["category"],
            }
        )

    records = list(groups.values())
    for record in records:
        record["tool_count"] = len(record["tools"])
    records.sort(key=lambda item: (item["platform"], item["name"].lower()))
    return records
