"""把本机统计导出为网页版使用的静态快照。

网页版托管在 GitHub Pages 上，没有后端，也读不到本机日志，所以用量数据在构建时
导出成一份 JSON。导出时会先把家目录替换成 `~`，避免把用户名带进公开仓库。

用法：
    python backend/scripts/export_snapshot.py --scan
默认写到 frontend/public/data/snapshot.json。
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

from app import pricing, services  # noqa: E402
from app.collectors import agents, mcp, skills  # noqa: E402
from app.scan import run_scan  # noqa: E402
from app.store import db  # noqa: E402

OUT_PATH = ROOT / "frontend" / "public" / "data" / "snapshot.json"
HOME = str(Path.home())


def _redact(value):
    """递归替换家目录路径，其余内容原样保留。"""
    if isinstance(value, str):
        return value.replace(HOME, "~").replace(HOME.replace("\\", "/"), "~")
    if isinstance(value, list):
        return [_redact(item) for item in value]
    if isinstance(value, dict):
        return {key: _redact(item) for key, item in value.items()}
    return value


def _skill_payload() -> dict:
    items = skills.collect()
    return {
        "skills": items,
        "total": len(items),
        "enabled": sum(1 for item in items if item["enabled"]),
    }


def _mcp_payload() -> dict:
    items = mcp.collect()
    return {"servers": items, "total": len(items)}


def _agent_payload() -> dict:
    items = agents.collect()
    return {"agents": items, "total": len(items)}


def _price_payload() -> dict:
    table = pricing.load()
    return {
        "currency": table.currency,
        "unit": table.unit,
        "verified": table.verified,
        "note": table.note,
        "models": table.models,
    }


def build(days: int) -> dict:
    conn = db.connect()
    try:
        return {
            "mode": "snapshot",
            "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
            "notice": "构建时导出的本机快照，不是实时数据；单价为未核对的示例参考价。",
            "overview": services.overview(conn),
            "daily": services.daily(conn, days),
            "models": services.models(conn),
            "skills": _skill_payload(),
            "mcp": _mcp_payload(),
            "agents": _agent_payload(),
            "prices": _price_payload(),
        }
    finally:
        conn.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="导出网页版静态快照")
    parser.add_argument("--scan", action="store_true", help="导出前先扫描一次日志")
    parser.add_argument("--days", type=int, default=90, help="导出多少天的按天数据")
    parser.add_argument("--out", default=str(OUT_PATH), help="输出文件路径")
    args = parser.parse_args()

    if args.scan:
        run_scan(False)

    data = _redact(build(args.days))
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    print(
        json.dumps(
            {
                "out": str(out),
                "skills": data["skills"]["total"],
                "mcp": data["mcp"]["total"],
                "agents": data["agents"]["total"],
                "models": len(data["models"]["models"]),
                "bytes": out.stat().st_size,
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
