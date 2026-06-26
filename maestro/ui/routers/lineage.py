from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from maestro.ui.routers.pipelines import _checkpoint_to_dict

router = APIRouter()


@router.get("/lineage", response_class=HTMLResponse)
async def lineage_page(request: Request):
    templates = request.app.state.templates
    lineage_url = getattr(request.app.state, "lineage_url", None)
    store = request.app.state.store
    checkpoints = store.list_all()

    return templates.TemplateResponse(
        request,
        "lineage.html",
        {
            "active": "lineage",
            "lineage_url": lineage_url,
            "pipelines": [_checkpoint_to_dict(cp) for cp in checkpoints],
        },
    )
