"""接口用到的统计：总览、按天、按模型。"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app import pricing
from app.collectors import agents, mcp, skills
from app.scan import last_scan
from app.store import db

TOKEN_COLUMNS = (
    "input_tokens",
    "output_tokens",
    "cache_read_tokens",
    "cache_write_tokens",
)
EMPTY_MODELS = {"", "unknown", "<synthetic>"}


def _parse_time(value: str | None) -> datetime | None:
    if not value:
        return None
    text = value.strip().replace("Z", "+00:00")
    try:
        moment = datetime.fromisoformat(text)
    except ValueError:
        return None
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    return moment.astimezone()


def _tokens(row: dict) -> int:
    return sum(int(row.get(column) or 0) for column in TOKEN_COLUMNS)


def _usage_rows(conn) -> list[dict]:
    rows = conn.execute(
        """
        SELECT timestamp, source, model,
               input_tokens, output_tokens,
               cache_read_tokens, cache_write_tokens
        FROM usage_events
        """
    )
    return [dict(row) for row in rows]


def _cost(table, model: str, row: dict) -> float | None:
    return pricing.cost_of(table, model, row)


def overview(conn) -> dict:
    table = pricing.load()
    rows = _usage_rows(conn)
    now = datetime.now().astimezone()
    today = now.date()
    week_start = (now - timedelta(days=6)).date()

    total_tokens = 0
    total_cost = 0.0
    unpriced_tokens = 0
    today_tokens = 0
    today_cost = 0.0
    active_models: set[str] = set()
    by_source: dict[str, dict] = {}
    by_model: dict[tuple[str, str], dict] = {}

    for row in rows:
        tokens = _tokens(row)
        model = row["model"] or "unknown"
        cost = _cost(table, model, row)
        moment = _parse_time(row["timestamp"])

        total_tokens += tokens
        if cost is None:
            unpriced_tokens += tokens
        else:
            total_cost += cost

        source = by_source.setdefault(
            row["source"], {"tokens": 0, "cost": 0.0, "unpriced_tokens": 0, "events": 0}
        )
        source["tokens"] += tokens
        source["events"] += 1
        if cost is None:
            source["unpriced_tokens"] += tokens
        else:
            source["cost"] += cost

        key = (row["source"], model)
        bucket = by_model.setdefault(
            key, {"source": row["source"], "model": model, "tokens": 0, "cost": 0.0}
        )
        bucket["tokens"] += tokens
        if cost is not None:
            bucket["cost"] += cost

        if moment is not None:
            if moment.date() == today:
                today_tokens += tokens
                if cost is not None:
                    today_cost += cost
            if moment.date() >= week_start and model not in EMPTY_MODELS:
                active_models.add(model)

    sessions = sum(item["sessions"] for item in db.summary(conn))
    top_models = sorted(by_model.values(), key=lambda item: item["tokens"], reverse=True)

    skill_items = skills.collect()
    mcp_items = mcp.collect()
    agent_items = agents.collect()

    return {
        "totals": {
            "tokens": total_tokens,
            "cost": round(total_cost, 4),
            "unpriced_tokens": unpriced_tokens,
            "events": len(rows),
            "sessions": sessions,
        },
        "today": {
            "date": today.isoformat(),
            "tokens": today_tokens,
            "cost": round(today_cost, 4),
        },
        "active_models": sorted(active_models),
        "by_source": [
            {
                "source": name,
                "tokens": value["tokens"],
                "cost": round(value["cost"], 4),
                "unpriced_tokens": value["unpriced_tokens"],
            }
            for name, value in sorted(by_source.items())
        ],
        "top_models": [
            {
                "source": item["source"],
                "model": item["model"],
                "tokens": item["tokens"],
                "cost": round(item["cost"], 4),
            }
            for item in top_models[:5]
        ],
        "counts": {
            "skills": len(skill_items),
            "enabled_skills": sum(1 for item in skill_items if item["enabled"]),
            "mcps": len(mcp_items),
            "agents": len(agent_items),
        },
        "prices": {
            "currency": table.currency,
            "verified": table.verified,
            "note": table.note,
        },
        "last_scan": last_scan(conn),
    }


def daily(conn, days: int = 30) -> dict:
    """最近 N 个自然日的 token 与花费，没有记录的日期补 0。"""
    table = pricing.load()
    rows = _usage_rows(conn)
    today = datetime.now().astimezone().date()
    start = today - timedelta(days=days - 1)

    buckets: dict[str, dict] = {}
    for offset in range(days):
        day = (start + timedelta(days=offset)).isoformat()
        buckets[day] = {
            "date": day,
            "tokens": 0,
            "cost": 0.0,
            "unpriced_tokens": 0,
            "claude_tokens": 0,
            "trae_tokens": 0,
        }

    for row in rows:
        moment = _parse_time(row["timestamp"])
        if moment is None:
            continue
        day = moment.date().isoformat()
        bucket = buckets.get(day)
        if bucket is None:
            continue

        tokens = _tokens(row)
        cost = _cost(table, row["model"] or "unknown", row)
        bucket["tokens"] += tokens
        if cost is None:
            bucket["unpriced_tokens"] += tokens
        else:
            bucket["cost"] += cost
        if row["source"] == "claude":
            bucket["claude_tokens"] += tokens
        elif row["source"] == "trae":
            bucket["trae_tokens"] += tokens

    return {
        "days": [buckets[key] for key in sorted(buckets)],
        "currency": table.currency,
    }


def models(conn) -> dict:
    table = pricing.load()
    ranked = sorted(
        (row for row in db.model_counts(conn) if row["tokens"] > 0),
        key=lambda item: item["tokens"],
        reverse=True,
    )

    result = []
    for row in ranked:
        detail = conn.execute(
            """
            SELECT SUM(input_tokens) AS input_tokens,
                   SUM(output_tokens) AS output_tokens,
                   SUM(cache_read_tokens) AS cache_read_tokens,
                   SUM(cache_write_tokens) AS cache_write_tokens
            FROM usage_events
            WHERE source = ? AND model = ?
            """,
            (row["source"], row["model"]),
        ).fetchone()
        usage = dict(detail) if detail else {}
        cost = _cost(table, row["model"], usage)
        result.append(
            {
                "source": row["source"],
                "model": row["model"],
                "events": row["events"],
                "tokens": row["tokens"],
                "cost": None if cost is None else round(cost, 4),
                "unpriced": cost is None,
                "input_tokens": usage.get("input_tokens") or 0,
                "output_tokens": usage.get("output_tokens") or 0,
                "cache_read_tokens": usage.get("cache_read_tokens") or 0,
                "cache_write_tokens": usage.get("cache_write_tokens") or 0,
            }
        )

    return {
        "models": result,
        "currency": table.currency,
        "verified": table.verified,
        "note": table.note,
    }
