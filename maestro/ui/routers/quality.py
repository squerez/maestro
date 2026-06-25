from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

router = APIRouter()


def _collect_dq_metrics() -> dict:
    try:
        from prometheus_client import REGISTRY

        dq: dict[tuple[str, str], float] = {}
        dlq: dict[tuple[str, str], float] = {}

        for metric in REGISTRY.collect():
            if metric.name == "dq_failures_total":
                for s in metric.samples:
                    if s.name == "dq_failures_total":
                        key = (s.labels.get("pipeline", "?"), s.labels.get("suite", "?"))
                        dq[key] = dq.get(key, 0) + s.value
            elif metric.name == "dlq_records_total":
                for s in metric.samples:
                    if s.name == "dlq_records_total":
                        key = (s.labels.get("pipeline", "?"), s.labels.get("strategy", "?"))
                        dlq[key] = dlq.get(key, 0) + s.value

        return {
            "dq": [
                {"pipeline": k[0], "suite": k[1], "failures": f"{v:.0f}"}
                for k, v in sorted(dq.items(), key=lambda x: x[1], reverse=True)
            ],
            "dlq": [
                {"pipeline": k[0], "strategy": k[1], "records": f"{v:.0f}"}
                for k, v in sorted(dlq.items(), key=lambda x: x[1], reverse=True)
            ],
        }
    except Exception:
        return {"dq": [], "dlq": []}


@router.get("/quality", response_class=HTMLResponse)
async def quality_page(request: Request):
    templates = request.app.state.templates
    store = request.app.state.store
    checkpoints = store.list_all()
    dq_data = _collect_dq_metrics()

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
        "quality.html",
        {
            "active": "quality",
            "pipelines": pipelines,
            "dq_failures": dq_data["dq"],
            "dlq_records": dq_data["dlq"],
        },
    )
