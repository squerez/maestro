from __future__ import annotations

from dataclasses import dataclass, field
from typing import List


@dataclass
class MaestroConfig:
    """
    Global framework configuration.

    Per-pipeline settings live in PipelineSpec (loaded from YAML).
    This controls host-level defaults shared across all pipelines.
    """

    checkpoint_dir: str = "~/.maestro/checkpoints"
    plugin_packages: List[str] = field(
        default_factory=lambda: [
            "toolbox.maestro.runtimes",
            "toolbox.maestro.plugins",
            "toolbox.maestro.transforms",
        ]
    )
    default_runtime: str = "polars"
