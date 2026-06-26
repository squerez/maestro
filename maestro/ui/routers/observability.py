from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, PlainTextResponse

router = APIRouter()

_MAESTRO_METRIC_NAMES = {
    "pipeline_runs_total",
    "pipeline_duration_seconds",
    "records_processed_total",
    "dq_failures_total",
    "sla_breaches_total",
    "dlq_records_total",
}


def _collect_metrics() -> list[dict]:
    try:
        from prometheus_client import REGISTRY

        rows = []
        for metric in REGISTRY.collect():
            if not any(metric.name.startswith(n) for n in _MAESTRO_METRIC_NAMES):
                continue
            for s in metric.samples:
                if s.name.endswith("_created"):
                    continue
                rows.append({
                    "name": s.name,
                    "labels": ", ".join(f'{k}="{v}"' for k, v in s.labels.items()),
                    "value": f"{s.value:.6g}",
                })
        return rows
    except Exception:
        return []


@router.get("/observability", response_class=HTMLResponse)
async def observability_page(request: Request):
    templates = request.app.state.templates
    metrics = _collect_metrics()
    return templates.TemplateResponse(
        request,
        "observability.html",
        {"active": "observability", "metrics": metrics},
    )


@router.get("/api/metrics/raw", response_class=PlainTextResponse)
async def raw_metrics():
    from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

    return PlainTextResponse(generate_latest().decode("utf-8"), media_type=CONTENT_TYPE_LATEST)
