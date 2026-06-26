from __future__ import annotations

from pathlib import Path
from typing import List, Optional

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from maestro.pipeline.state import CheckpointStore
from maestro.plugins.discovery import discover_plugins

_UI_DIR = Path(__file__).parent


_BUILTIN_PACKAGES = ["maestro.runtimes", "maestro.plugins", "maestro.transforms"]


def create_app(
    checkpoint_dir: str = "~/.maestro/checkpoints",
    plugin_packages: Optional[List[str]] = None,
    grafana_url: Optional[str] = None,
    lineage_url: Optional[str] = None,
    ge_docs_dir: Optional[str] = None,
) -> FastAPI:
    for pkg in _BUILTIN_PACKAGES + (plugin_packages or []):
        discover_plugins(pkg)

    store = CheckpointStore(checkpoint_dir)
    templates = Jinja2Templates(directory=_UI_DIR / "templates")

    app = FastAPI(title="Maestro", version="0.1.0", docs_url="/api/docs")
    app.state.store = store
    app.state.templates = templates
    app.state.grafana_url = grafana_url
    app.state.lineage_url = lineage_url
    app.state.ge_docs_url = "/quality/docs" if ge_docs_dir else None

    app.mount("/static", StaticFiles(directory=_UI_DIR / "static"), name="static")

    if ge_docs_dir:
        docs_path = Path(ge_docs_dir).expanduser()
        docs_path.mkdir(parents=True, exist_ok=True)
        app.mount("/quality/docs", StaticFiles(directory=docs_path, html=True), name="ge-docs")

    import os
    from prometheus_client import CollectorRegistry, make_asgi_app

    if os.environ.get("PROMETHEUS_MULTIPROC_DIR"):
        from prometheus_client.multiprocess import MultiProcessCollector
        _registry = CollectorRegistry()
        MultiProcessCollector(_registry)
        _metrics_app = make_asgi_app(registry=_registry)
    else:
        _metrics_app = make_asgi_app()

    app.mount("/metrics", _metrics_app)

    from maestro.ui.routers.grafana import router as grafana_router
    from maestro.ui.routers.lineage import router as lineage_router
    from maestro.ui.routers.observability import router as observability_router
    from maestro.ui.routers.pipelines import router as pipelines_router
    from maestro.ui.routers.quality import router as quality_router
    from maestro.ui.routers.transforms import router as transforms_router

    app.include_router(pipelines_router)
    app.include_router(transforms_router)
    app.include_router(observability_router)
    app.include_router(grafana_router)
    app.include_router(quality_router)
    app.include_router(lineage_router)

    return app


def serve(
    host: str = "0.0.0.0",
    port: int = 8080,
    checkpoint_dir: str = "~/.maestro/checkpoints",
    plugin_packages: Optional[List[str]] = None,
    grafana_url: Optional[str] = None,
    lineage_url: Optional[str] = None,
    ge_docs_dir: Optional[str] = None,
) -> None:
    import uvicorn

    app = create_app(checkpoint_dir, plugin_packages, grafana_url, lineage_url, ge_docs_dir)
    uvicorn.run(app, host=host, port=port)
