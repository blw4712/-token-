"""本地 API：只监听 127.0.0.1，供 Electron 面板和桌宠读取。"""

from __future__ import annotations

import asyncio
import json
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import Body, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app import pricing, services
from app.collectors import agents, mcp, skills
from app.config import PRICES_PATH
from app.scan import run_scan
from app.store import db

ROOT = Path(__file__).resolve().parents[2]
FRONTEND_DIST = ROOT / "frontend" / "dist"


@asynccontextmanager
async def lifespan(app: FastAPI):
    await asyncio.to_thread(run_scan, False)
    yield


app = FastAPI(title="Agent Console", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health() -> dict:
    return {"ok": True}


@app.get("/api/overview")
def get_overview() -> dict:
    conn = db.connect()
    try:
        return services.overview(conn)
    finally:
        conn.close()


@app.get("/api/daily")
def get_daily(days: int = Query(30, ge=1, le=90)) -> dict:
    conn = db.connect()
    try:
        return services.daily(conn, days)
    finally:
        conn.close()


@app.get("/api/models")
def get_models() -> dict:
    conn = db.connect()
    try:
        return services.models(conn)
    finally:
        conn.close()


@app.get("/api/skills")
def get_skills() -> dict:
    items = skills.collect()
    return {
        "skills": items,
        "total": len(items),
        "enabled": sum(1 for item in items if item["enabled"]),
    }


@app.get("/api/mcp")
def get_mcp() -> dict:
    items = mcp.collect()
    return {"servers": items, "total": len(items)}


@app.get("/api/agents")
def get_agents() -> dict:
    items = agents.collect()
    return {"agents": items, "total": len(items)}


@app.get("/api/prices")
def get_prices() -> dict:
    table = pricing.load()
    return {
        "currency": table.currency,
        "unit": table.unit,
        "verified": table.verified,
        "note": table.note,
        "models": table.models,
    }


@app.put("/api/prices")
def put_prices(payload: dict = Body(...)) -> dict:
    models = payload.get("models")
    if not isinstance(models, dict) or not models:
        raise HTTPException(status_code=400, detail="缺少 models")

    for name, rates in models.items():
        if rates is None:
            continue
        if not isinstance(rates, dict):
            raise HTTPException(status_code=400, detail=f"{name} 的单价格式不对")
        for field in pricing.PRICE_FIELDS:
            value = rates.get(field)
            if value is None:
                continue
            if isinstance(value, bool) or not isinstance(value, (int, float)) or value < 0:
                raise HTTPException(
                    status_code=400, detail=f"{name} 的 {field} 需要非负数字"
                )

    current = json.loads(PRICES_PATH.read_text(encoding="utf-8"))
    current["models"] = models
    current["verified"] = bool(payload.get("verified", current.get("verified", False)))
    PRICES_PATH.write_text(
        json.dumps(current, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    table = pricing.load()
    return {
        "currency": table.currency,
        "unit": table.unit,
        "verified": table.verified,
        "note": table.note,
        "models": table.models,
        "saved": True,
    }


@app.post("/api/scan")
async def trigger_scan(full: bool = Query(False)) -> dict[str, Any]:
    return await asyncio.to_thread(run_scan, full)


if FRONTEND_DIST.is_dir():
    app.mount("/", StaticFiles(directory=FRONTEND_DIST, html=True), name="panel")
