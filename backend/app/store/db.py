"""SQLite 存储：建表、按文件增量同步、基础统计。"""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

from app.config import DB_PATH

SCHEMA = """
CREATE TABLE IF NOT EXISTS scan_files (
    path TEXT PRIMARY KEY,
    source TEXT NOT NULL,
    mtime REAL NOT NULL,
    size INTEGER NOT NULL,
    rows INTEGER NOT NULL DEFAULT 0,
    parsed_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS usage_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source TEXT NOT NULL,
    file_path TEXT NOT NULL,
    session_id TEXT NOT NULL,
    message_id TEXT,
    timestamp TEXT,
    model TEXT,
    input_tokens INTEGER NOT NULL DEFAULT 0,
    output_tokens INTEGER NOT NULL DEFAULT 0,
    cache_read_tokens INTEGER NOT NULL DEFAULT 0,
    cache_write_tokens INTEGER NOT NULL DEFAULT 0,
    is_synthetic INTEGER NOT NULL DEFAULT 0,
    blocks INTEGER NOT NULL DEFAULT 1
);

CREATE INDEX IF NOT EXISTS idx_usage_source
    ON usage_events(source, session_id);
CREATE INDEX IF NOT EXISTS idx_usage_time ON usage_events(timestamp);
CREATE INDEX IF NOT EXISTS idx_usage_model ON usage_events(model);
CREATE UNIQUE INDEX IF NOT EXISTS uniq_usage
    ON usage_events(source, session_id, message_id)
    WHERE message_id IS NOT NULL;
"""

INSERT_SQL = """
INSERT OR REPLACE INTO usage_events
    (source, file_path, session_id, message_id, timestamp, model,
     input_tokens, output_tokens, cache_read_tokens, cache_write_tokens,
     is_synthetic, blocks)
VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
"""


def connect(db_path: Path | None = None) -> sqlite3.Connection:
    path = db_path or DB_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.executescript(SCHEMA)
    return conn


def _row(source: str, path: Path, record: dict) -> tuple:
    return (
        source,
        str(path),
        record["session_id"],
        record.get("message_id"),
        record.get("timestamp"),
        record.get("model") or "unknown",
        int(record.get("input_tokens") or 0),
        int(record.get("output_tokens") or 0),
        int(record.get("cache_read_tokens") or 0),
        int(record.get("cache_write_tokens") or 0),
        1 if record.get("is_synthetic") else 0,
        int(record.get("blocks") or 1),
    )


def sync_source(
    conn: sqlite3.Connection,
    source: str,
    files: Iterable[Path],
    parse,
    force: bool = False,
) -> dict:
    """按文件修改时间和大小做增量同步，返回本次统计。"""
    paths = [Path(item) for item in files]
    stats = {
        "source": source,
        "files": len(paths),
        "parsed": 0,
        "skipped": 0,
        "rows": 0,
        "errors": 0,
        "removed": 0,
    }

    if force:
        conn.execute("DELETE FROM usage_events WHERE source = ?", (source,))
        conn.execute("DELETE FROM scan_files WHERE source = ?", (source,))

    known = {
        row["path"]: row
        for row in conn.execute(
            "SELECT path, mtime, size FROM scan_files WHERE source = ?", (source,)
        )
    }

    seen: set[str] = set()
    for path in paths:
        key = str(path)
        seen.add(key)
        try:
            stat = path.stat()
        except OSError:
            stats["errors"] += 1
            continue

        previous = known.get(key)
        unchanged = (
            not force
            and previous is not None
            and previous["size"] == stat.st_size
            and abs(previous["mtime"] - round(stat.st_mtime, 3)) < 1e-6
        )
        if unchanged:
            stats["skipped"] += 1
            continue

        try:
            records = parse(path)
        except Exception:  # 单个文件解析失败不影响其它文件
            stats["errors"] += 1
            continue

        conn.execute("DELETE FROM usage_events WHERE file_path = ?", (key,))
        if records:
            conn.executemany(
                INSERT_SQL, [_row(source, path, record) for record in records]
            )
        conn.execute(
            """
            INSERT INTO scan_files (path, source, mtime, size, rows, parsed_at)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(path) DO UPDATE SET
                source = excluded.source,
                mtime = excluded.mtime,
                size = excluded.size,
                rows = excluded.rows,
                parsed_at = excluded.parsed_at
            """,
            (
                key,
                source,
                round(stat.st_mtime, 3),
                stat.st_size,
                len(records),
                datetime.now(timezone.utc).isoformat(),
            ),
        )
        stats["parsed"] += 1
        stats["rows"] += len(records)

    for stale in set(known) - seen:
        conn.execute("DELETE FROM usage_events WHERE file_path = ?", (stale,))
        conn.execute("DELETE FROM scan_files WHERE path = ?", (stale,))
        stats["removed"] += 1

    conn.commit()
    return stats


def summary(conn: sqlite3.Connection) -> list[dict]:
    rows = conn.execute(
        """
        SELECT source,
               COUNT(*) AS events,
               COUNT(DISTINCT session_id) AS sessions,
               SUM(input_tokens) AS input_tokens,
               SUM(output_tokens) AS output_tokens,
               SUM(cache_read_tokens) AS cache_read_tokens,
               SUM(cache_write_tokens) AS cache_write_tokens,
               MIN(timestamp) AS first_seen,
               MAX(timestamp) AS last_seen
        FROM usage_events
        GROUP BY source
        ORDER BY source
        """
    )
    return [dict(row) for row in rows]


def model_counts(conn: sqlite3.Connection) -> list[dict]:
    rows = conn.execute(
        """
        SELECT source, model, COUNT(*) AS events,
               SUM(input_tokens + output_tokens
                   + cache_read_tokens + cache_write_tokens) AS tokens
        FROM usage_events
        GROUP BY source, model
        ORDER BY tokens DESC
        """
    )
    return [dict(row) for row in rows]
