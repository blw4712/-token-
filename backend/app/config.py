"""本地路径配置。

所有数据目录都允许通过环境变量覆盖，便于测试时指向样例数据。
"""

from __future__ import annotations

import os
from pathlib import Path

CLAUDE_HOME = Path(
    os.environ.get("AGENT_CONSOLE_CLAUDE_HOME") or Path.home() / ".claude"
)
CLAUDE_PROJECTS = CLAUDE_HOME / "projects"
CLAUDE_SKILLS = CLAUDE_HOME / "skills"
CLAUDE_AGENTS = CLAUDE_HOME / "agents"
CLAUDE_JSON = CLAUDE_HOME.parent / ".claude.json"

TRAE_HOME = Path(
    os.environ.get("AGENT_CONSOLE_TRAE_HOME") or Path.home() / ".trae-cn"
)
TRAE_EVENTS = TRAE_HOME / "hub_event_cache"
TRAE_SKILLS = TRAE_HOME / "builtin_skills"
TRAE_PLUGINS = TRAE_HOME / "plugins"
TRAE_MCPS = TRAE_HOME / "mcps"
TRAE_ASSISTANT = TRAE_HOME / "assistant"
TRAE_SKILL_CONFIG = TRAE_HOME / "skill-config.json"
TRAE_PLUGIN_INSTALLED = TRAE_HOME / "installed-plugins.json"

DATA_DIR = Path(
    os.environ.get("AGENT_CONSOLE_DATA") or Path.home() / ".agent-console"
)
DB_PATH = DATA_DIR / "agent_console.db"
SERVER_PATH = Path(
    os.environ.get("AGENT_CONSOLE_SERVER") or DATA_DIR / "server.json"
)

# 价格表放在代码目录，方便直接编辑，后续界面也写这份文件。
PRICES_PATH = Path(__file__).resolve().parents[1] / "prices.json"
