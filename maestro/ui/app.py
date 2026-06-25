from __future__ import annotations

from pathlib import Path
from typing import List, Optional

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from toolbox.maestro.pipeline.state import CheckpointStore
from toolbox.maestro.plugins.discovery import discover_plugins

_UI_DIR = Path(__file__).parent


def create_app(
    checkpoint_dir: str = "~/.maestro/checkpoints",
    plugin_packages: Optional[List[str]] = None,
    grafana_url: Optional[str] = None,
    lineage_url: Optional[str] = None,
) -> FastAPI:
    for pkg in plugin_packages or []:
        discover_plugins(pkg)

    store = CheckpointStore(checkpoint_dir)
    templates = Jinja2Templates(directory=_UI_DIR / "templates")

    app = FastAPI(title="Maestro", version="0.1.0", docs_url="/api/docs")
    app.state.store = store
    app.state.templates = templates
    app.state.grafana_url = grafana_url
    app.state.lineage_url = lineage_url

    app.mount("/static", StaticFiles(directory=_UI_DIR / "static"), name="static")

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

    from toolbox.maestro.ui.routers.grafana import router as grafana_router
    from toolbox.maestro.ui.routers.lineage import router as lineage_router
    from toolbox.maestro.ui.routers.observability import router as observability_router
    from toolbox.maestro.ui.routers.pipelines import router as pipelines_router
    from toolbox.maestro.ui.routers.quality import router as quality_router
    from toolbox.maestro.ui.routers.transforms import router as transforms_router

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
    reload: bool = False,
    grafana_url: Optional[str] = None,
    lineage_url: Optional[str] = None,
) -> None:
    import uvicorn

    app = create_app(checkpoint_dir, plugin_packages, grafana_url, lineage_url)
    uvicorn.run(app, host=host, port=port, reload=reload)
