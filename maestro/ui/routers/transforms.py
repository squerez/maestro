from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

router = APIRouter()


def _get_templates(request: Request) -> Jinja2Templates:
    return request.app.state.templates


def _transforms_list() -> list[dict]:
    try:
        from toolbox.maestro.transforms.registry import TransformRegistry

        out = []
        for meta in TransformRegistry.list_all():
            out.append(
                {
                    "name": meta.name,
                    "description": meta.description or "—",
                    "tags": meta.tags,
                    "input_schema": [
                        {"name": c.name, "type": c.type} for c in meta.input_schema
                    ],
                    "output_schema": [
                        {"name": c.name, "type": c.type} for c in meta.output_schema
                    ],
                }
            )
        return out
    except Exception:
        return []


@router.get("/transforms", response_class=HTMLResponse)
async def transforms_page(request: Request, tag: str = ""):
    templates = _get_templates(request)
    transforms = _transforms_list()
    all_tags = sorted({t for tr in transforms for t in tr["tags"]})
    filtered = [tr for tr in transforms if not tag or tag in tr["tags"]]

    return templates.TemplateResponse(
        request,
        "transforms.html",
        {
            "active": "transforms",
            "transforms": filtered,
            "all_tags": all_tags,
            "active_tag": tag,
            "total": len(transforms),
        },
    )


@router.get("/api/transforms")
async def api_transforms():
    return _transforms_list()
