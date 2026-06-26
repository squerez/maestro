from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse

router = APIRouter()

_DASHBOARD_PATH = Path(__file__).parent.parent.parent / "grafana" / "maestro_dashboard.json"


def _load_dashboard() -> dict | None:
    try:
        return json.loads(_DASHBOARD_PATH.read_text())
    except Exception:
        return None


@router.get("/grafana", response_class=HTMLResponse)
async def grafana_page(request: Request):
    templates = request.app.state.templates
    grafana_url = getattr(request.app.state, "grafana_url", None)

    # Also collect any per-pipeline grafana_url from checkpoints
    store = request.app.state.store
    pipeline_links = [
        {"name": cp.pipeline, "url": cp.extra["grafana_url"]}
        for cp in store.list_all()
        if cp.extra and cp.extra.get("grafana_url")
    ]

    return templates.TemplateResponse(
        request,
        "grafana.html",
        {
            "active": "grafana",
            "grafana_url": grafana_url,
            "pipeline_links": pipeline_links,
            "dashboard_path": str(_DASHBOARD_PATH) if _DASHBOARD_PATH.exists() else None,
        },
    )


@router.get("/api/grafana/dashboard")
async def grafana_dashboard():
    dashboard = _load_dashboard()
    if dashboard is None:
        raise HTTPException(status_code=404, detail="Dashboard file not found")
    return JSONResponse(dashboard)
