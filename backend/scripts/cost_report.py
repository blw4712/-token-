"""费用报表：按模型和按天汇总 token 并计算花费。

用法：
    python backend/scripts/cost_report.py
"""

from __future__ import annotations

import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

from app import pricing  # noqa: E402
from app.store import db  # noqa: E402

MODEL_SQL = """
SELECT source, model,
       COUNT(*) AS events,
       SUM(input_tokens) AS input_tokens,
       SUM(output_tokens) AS output_tokens,
       SUM(cache_read_tokens) AS cache_read_tokens,
       SUM(cache_write_tokens) AS cache_write_tokens,
       SUM(input_tokens + output_tokens
           + cache_read_tokens + cache_write_tokens) AS total_tokens
FROM usage_events
GROUP BY source, model
ORDER BY total_tokens DESC
"""

DAY_SQL = """
SELECT substr(timestamp, 1, 10) AS day, model,
       SUM(input_tokens) AS input_tokens,
       SUM(output_tokens) AS output_tokens,
       SUM(cache_read_tokens) AS cache_read_tokens,
       SUM(cache_write_tokens) AS cache_write_tokens,
       SUM(input_tokens + output_tokens
           + cache_read_tokens + cache_write_tokens) AS total_tokens
FROM usage_events
WHERE timestamp IS NOT NULL
GROUP BY day, model
ORDER BY day DESC
"""


def main() -> int:
    table = pricing.load()
    conn = db.connect()

    flag = "已核对" if table.verified else "未核对，示例价"
    print(f"价格表  {table.currency} / 每百万 token  {flag}")
    if table.note:
        print(f"说明    {table.note}")

    print("\n按模型")
    priced_total = 0.0
    unpriced_tokens = 0
    all_tokens = 0
    for row in conn.execute(MODEL_SQL):
        cost = pricing.cost_of(table, row["model"], row)
        all_tokens += row["total_tokens"]
        if cost is None:
            unpriced_tokens += row["total_tokens"]
            cost_text = "待定价"
        else:
            priced_total += cost
            cost_text = f"{cost:>10.2f}"
        print(
            f"  {row['source']:<7} {row['model']:<22}"
            f" {row['events']:>4} 条  {row['total_tokens']:>12,} token"
            f"  {cost_text}"
        )

    print(f"\n已计价合计  {priced_total:.2f} {table.currency}")
    unpriced_share = unpriced_tokens / all_tokens * 100 if all_tokens else 0
    print(f"待定价 token  {unpriced_tokens:,} / {all_tokens:,}（{unpriced_share:.1f}%）")

    print("\n按天")
    daily: dict[str, dict] = {}
    for row in conn.execute(DAY_SQL):
        cost = pricing.cost_of(table, row["model"], row)
        bucket = daily.setdefault(
            row["day"], {"cost": 0.0, "priced": 0, "unpriced_tokens": 0}
        )
        if cost is None:
            bucket["unpriced_tokens"] += row["total_tokens"]
        else:
            bucket["cost"] += cost
            bucket["priced"] += row["total_tokens"]

    for day in sorted(daily, reverse=True)[:10]:
        bucket = daily[day]
        print(
            f"  {day}  已计价 {bucket['priced']:>11,} token"
            f"  {bucket['cost']:>8.2f} {table.currency}"
            f"  待定价 {bucket['unpriced_tokens']:>10,} token"
        )

    conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
