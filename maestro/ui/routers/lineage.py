from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

router = APIRouter()


@router.get("/lineage", response_class=HTMLResponse)
async def lineage_page(request: Request):
    templates = request.app.state.templates
    lineage_url = getattr(request.app.state, "lineage_url", None)
    store = request.app.state.store
    checkpoints = store.list_all()

    pipelines = [
        {
            "name": cp.pipeline,
            "status": cp.status,
            "last_run": cp.last_run.strftime("%Y-%m-%d %H:%M UTC"),
            "records": f"{cp.records_processed:,}",
        }
        for cp in checkpoints
    ]

    return templates.TemplateResponse(
        request,
        "lineage.html",
        {
            "active": "lineage",
            "lineage_url": lineage_url,
            "pipelines": pipelines,
        },
    )
