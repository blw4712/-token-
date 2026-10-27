"""价格表加载与费用计算。

价格单位统一为"每百万 token"，币种写在 prices.json 里。
任何一项单价缺失，该模型就按待定价处理，返回 None，不会当成 0 元。
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from app.config import PRICES_PATH

PRICE_FIELDS = ("input", "output", "cache_read", "cache_write")
TOKEN_FIELDS = {
    "input": "input_tokens",
    "output": "output_tokens",
    "cache_read": "cache_read_tokens",
    "cache_write": "cache_write_tokens",
}
UNIT = "per_1m_tokens"


@dataclass(frozen=True)
class PriceTable:
    currency: str
    unit: str
    verified: bool
    note: str
    models: dict[str, dict | None]


def _rate(value: object) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    rate = float(value)
    return rate if rate >= 0 else None


def load(path: Path | None = None) -> PriceTable:
    source = Path(path or PRICES_PATH)
    raw = json.loads(source.read_text(encoding="utf-8"))
    unit = raw.get("unit") or UNIT
    if unit != UNIT:
        raise ValueError(f"不支持的价格单位：{unit}")

    models: dict[str, dict | None] = {}
    for name, rates in (raw.get("models") or {}).items():
        if not isinstance(rates, dict):
            models[name] = None
            continue
        models[name] = {field: _rate(rates.get(field)) for field in PRICE_FIELDS}

    return PriceTable(
        currency=str(raw.get("currency") or "CNY"),
        unit=unit,
        verified=bool(raw.get("verified")),
        note=str(raw.get("note") or ""),
        models=models,
    )


def rates_for(table: PriceTable, model: str) -> dict | None:
    """返回完整的四档单价，缺任意一档都算待定价。"""
    rates = table.models.get(model)
    if not rates:
        return None
    if any(rates[field] is None for field in PRICE_FIELDS):
        return None
    return rates


def _token(usage: object, key: str) -> int:
    """兼容字典和 sqlite3.Row 两种取值方式。"""
    try:
        value = usage[key]  # type: ignore[index]
    except (KeyError, IndexError, TypeError):
        return 0
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def cost_of(table: PriceTable, model: str, usage: dict) -> float | None:
    """按 token 用量算钱，单价缺失时返回 None。"""
    rates = rates_for(table, model)
    if rates is None:
        return None
    return sum(
        _token(usage, TOKEN_FIELDS[field]) / 1_000_000 * rates[field]
        for field in PRICE_FIELDS
    )
