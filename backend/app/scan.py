"""扫描流程，脚本和接口共用。"""

from __future__ import annotations

from pathlib import Path

from app.collectors import claude, trae
from app.config import CLAUDE_PROJECTS, TRAE_EVENTS
from app.store import db


def parse_claude(path: Path) -> list[dict]:
    rows, _ = claude.parse_file(path)
    return claude.merge_records(rows)


def parse_trae(path: Path) -> list[dict]:
    rows, _ = trae.parse_file(path)
    return rows


def sync_all(conn, force: bool = False) -> list[dict]:
    return [
        db.sync_source(
            conn, "claude", claude.iter_session_files(CLAUDE_PROJECTS), parse_claude, force
        ),
        db.sync_source(
            conn, "trae", trae.iter_event_files(TRAE_EVENTS), parse_trae, force
        ),
    ]


def run_scan(force: bool = False) -> dict:
    conn = db.connect()
    try:
        stats = sync_all(conn, force)
        return {
            "stats": stats,
            "summary": db.summary(conn),
            "last_scan": last_scan(conn),
        }
    finally:
        conn.close()


def last_scan(conn) -> str | None:
    row = conn.execute("SELECT MAX(parsed_at) AS parsed_at FROM scan_files").fetchone()
    return row["parsed_at"] if row else None
