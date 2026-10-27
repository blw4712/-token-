"""对账脚本：核对 Claude Code 采集结果与真实日志是否一致。

用法：
    python backend/scripts/reconcile_claude.py
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

from app.collectors import claude  # noqa: E402


def scan_cost_state(files: list[Path]) -> tuple[int, float, int]:
    """读取客户端自带的金额记录，仅用于交叉核对，不参与费用计算。"""
    count = 0
    total = 0.0
    unknown = 0
    for path in files:
        with path.open("r", encoding="utf-8", errors="replace") as fh:
            for raw in fh:
                raw = raw.strip()
                if not raw or '"cost-state"' not in raw:
                    continue
                try:
                    obj = json.loads(raw)
                except json.JSONDecodeError:
                    continue
                if obj.get("type") != "cost-state":
                    continue
                count += 1
                total += float(obj.get("totalCostUSD") or 0)
                if obj.get("hasUnknownModelCost"):
                    unknown += 1
    return count, total, unknown


def main() -> int:
    files = list(claude.iter_session_files())
    raw_records: list[dict] = []
    bad_lines = 0
    for path in files:
        rows, bad = claude.parse_file(path)
        raw_records.extend(rows)
        bad_lines += bad

    records = claude.merge_records(raw_records)
    sessions = {r["session_id"] for r in records}
    models = Counter(r["model"] for r in records)
    ids = Counter(
        (r["session_id"], r["message_id"]) for r in records if r["message_id"]
    )
    duplicates = sum(n - 1 for n in ids.values() if n > 1)
    totals = {
        field: sum(r[field] for r in records) for field in claude.TOKEN_FIELDS
    }
    blocks = sum(r["blocks"] for r in records)

    print(f"会话文件        {len(files)}")
    print(f"会话 ID         {len(sessions)}")
    print(f"日志条目        {len(raw_records)}")
    print(f"模型回复        {len(records)}")
    print(f"合并条目        {blocks}")
    print(f"坏行            {bad_lines}")
    print(f"合并后重复 id   {duplicates}")
    print("模型分布        " + ", ".join(f"{m}={n}" for m, n in models.most_common()))
    print("token 合计      " + ", ".join(f"{k}={v:,}" for k, v in totals.items()))

    cost_count, cost_total, cost_unknown = scan_cost_state(files)
    print(
        f"客户端金额记录  {cost_count} 条，合计 {cost_total:.4f} 美元，"
        f"其中价格未知 {cost_unknown} 条"
    )

    per_session: dict[str, int] = {}
    for record in records:
        per_session[record["session_id"]] = per_session.get(
            record["session_id"], 0
        ) + sum(record[field] for field in claude.TOKEN_FIELDS)

    print("\ntoken 最多的 5 个会话：")
    for session_id, total in sorted(
        per_session.items(), key=lambda item: item[1], reverse=True
    )[:5]:
        print(f"  {session_id}  {total:,}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
