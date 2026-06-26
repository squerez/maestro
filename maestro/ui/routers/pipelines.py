from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from maestro.pipeline.state import Checkpoint, CheckpointStore

router = APIRouter()


def _get_deps(request: Request) -> tuple[Jinja2Templates, CheckpointStore]:
    return request.app.state.templates, request.app.state.store


def _checkpoint_to_dict(cp: Checkpoint) -> dict:
    return {
        "name": cp.pipeline,
        "status": cp.status,
        "last_run": cp.last_run.strftime("%Y-%m-%d %H:%M UTC"),
        "last_run_iso": cp.last_run.isoformat(),
        "records": f"{cp.records_processed:,}",
        "watermark": str(cp.last_watermark) if cp.last_watermark else "—",
        "grafana_url": cp.extra.get("grafana_url") if cp.extra else None,
    }


@router.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    templates, store = _get_deps(request)
    checkpoints = store.list_all()
    pipelines = [_checkpoint_to_dict(cp) for cp in checkpoints]

    total = len(pipelines)
    success = sum(1 for p in pipelines if p["status"] == "success")
    failed = sum(1 for p in pipelines if p["status"] == "failed")
    rate = f"{round(success / total * 100)}%" if total else "—"
    total_records = sum(cp.records_processed for cp in checkpoints)

    return templates.TemplateResponse(
        request,
        "index.html",
        {
            "active": "dashboard",
            "pipelines": pipelines,
            "stats": {
                "total": total,
                "success": success,
                "failed": failed,
                "rate": rate,
                "total_records": f"{total_records:,}",
            },
        },
    )


@router.get("/pipelines/{name}", response_class=HTMLResponse)
async def pipeline_detail(request: Request, name: str):
    templates, store = _get_deps(request)
    cp = store.load(name)
    pipeline = _checkpoint_to_dict(cp) if cp else None

    return templates.TemplateResponse(
        request,
        "pipeline.html",
        {
            "active": "dashboard",
            "pipeline": pipeline,
            "name": name,
        },
    )


@router.get("/api/pipelines")
async def api_pipelines(request: Request):
    _, store = _get_deps(request)
    return [_checkpoint_to_dict(cp) for cp in store.list_all()]


@router.get("/api/pipelines/{name}")
async def api_pipeline(request: Request, name: str):
    _, store = _get_deps(request)
    cp = store.load(name)
    if cp is None:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"Pipeline {name!r} not found")
    return _checkpoint_to_dict(cp)


@router.get("/api/health")
async def health():
    return {"status": "ok"}
