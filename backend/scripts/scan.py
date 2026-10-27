"""扫描入口：把两个平台的用量同步进 SQLite。

用法：
    python backend/scripts/scan.py
    python backend/scripts/scan.py --full
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

from app.config import DB_PATH  # noqa: E402
from app.scan import sync_all  # noqa: E402
from app.store import db  # noqa: E402


def print_stats(stats: list[dict], label: str) -> None:
    print(f"\n{label}")
    for item in stats:
        print(
            f"  {item['source']:<7} 文件 {item['files']:>3}  解析 {item['parsed']:>3}"
            f"  跳过 {item['skipped']:>3}  写入 {item['rows']:>4}"
            f"  清理 {item['removed']:>2}  失败 {item['errors']}"
        )


def print_summary(conn) -> None:
    print("\n按平台汇总")
    for row in db.summary(conn):
        print(
            f"  {row['source']:<7} 记录 {row['events']:>4}  会话 {row['sessions']:>3}"
            f"  输入 {row['input_tokens']:>10,}  输出 {row['output_tokens']:>9,}"
            f"  缓存读 {row['cache_read_tokens']:>11,}  缓存写 {row['cache_write_tokens']:>7,}"
        )
        print(f"          时间 {row['first_seen']} → {row['last_seen']}")

    print("\n模型分布")
    for row in db.model_counts(conn):
        print(
            f"  {row['source']:<7} {row['model']:<24} {row['events']:>4} 条"
            f"  {row['tokens']:>12,} token"
        )


def main() -> int:
    parser = argparse.ArgumentParser(description="扫描本地 Agent 用量")
    parser.add_argument("--full", action="store_true", help="忽略缓存全量重扫")
    args = parser.parse_args()

    conn = db.connect()
    first = sync_all(conn, args.full)
    print_stats(first, "第一次扫描" + ("（全量）" if args.full else "（增量）"))

    second = sync_all(conn, False)
    print_stats(second, "第二次扫描（验证增量）")

    print_summary(conn)
    size = DB_PATH.stat().st_size if DB_PATH.exists() else 0
    print(f"\n数据库  {DB_PATH}  {size / 1024:.1f} KB")
    conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
