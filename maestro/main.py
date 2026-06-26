from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

from maestro.config import MaestroConfig
from maestro.pipeline.engine import PipelineEngine
from maestro.pipeline.spec import PipelineSpec
from maestro.pipeline.state import CheckpointStore


def run(
    spec: PipelineSpec | str | Path | Dict[str, Any],
    config: Optional[MaestroConfig] = None,
) -> None:
    """
    Execute a pipeline.

    Args:
        spec: A PipelineSpec instance, a path to a YAML file, or a raw dict.
        config: Optional global framework config. Uses defaults if not provided.
    """
    cfg = config or MaestroConfig()

    if isinstance(spec, (str, Path)):
        pipeline = PipelineSpec.from_yaml(spec)
    elif isinstance(spec, dict):
        pipeline = PipelineSpec.from_dict(spec)
    else:
        pipeline = spec

    store = CheckpointStore(cfg.checkpoint_dir)
    engine = PipelineEngine(
        checkpoint_store=store,
        plugin_packages=cfg.plugin_packages,
    )
    engine.run(pipeline)
