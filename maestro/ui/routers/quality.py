from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from maestro.ui.routers.pipelines import _checkpoint_to_dict

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


def _collect_ge_results(checkpoints) -> list[dict]:
    rows = []
    for cp in checkpoints:
        dq_results = cp.extra.get("dq_results", {}) if cp.extra else {}
        for suite, result in dq_results.items():
            stats = result.get("statistics", {})
            rows.append({
                "pipeline": cp.pipeline,
                "suite": suite,
                "success": result.get("success", True),
                "last_run": cp.last_run.strftime("%Y-%m-%d %H:%M UTC"),
                "evaluated": stats.get("evaluated_expectations", "—"),
                "passed": stats.get("successful_expectations", "—"),
                "failed_count": stats.get("unsuccessful_expectations", "—"),
                "failed_expectations": result.get("failed_expectations", []),
            })
    return rows


@router.get("/quality", response_class=HTMLResponse)
async def quality_page(request: Request):
    templates = request.app.state.templates
    store = request.app.state.store
    checkpoints = store.list_all()
    dq_data = _collect_dq_metrics()
    ge_results = _collect_ge_results(checkpoints)

    return templates.TemplateResponse(
        request,
        "quality.html",
        {
            "active": "quality",
            "pipelines": [_checkpoint_to_dict(cp) for cp in checkpoints],
            "dq_failures": dq_data["dq"],
            "dlq_records": dq_data["dlq"],
            "ge_results": ge_results,
        },
    )
