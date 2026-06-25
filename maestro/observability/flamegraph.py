from __future__ import annotations

import contextlib
import time
from pathlib import Path
from typing import Generator

from loguru import logger


class PipelineProfiler:
    """
    Wraps pipeline execution with pyinstrument profiling, saving an HTML flamegraph.

    If pyinstrument is not installed, profiling degrades gracefully to a no-op.
    """

    def __init__(self, output_dir: str | Path = "~/.maestro/flamegraphs") -> None:
        self._dir = Path(output_dir).expanduser()
        self._dir.mkdir(parents=True, exist_ok=True)

    @contextlib.contextmanager
    def profile(self, pipeline: str) -> Generator[None, None, None]:
        try:
            from pyinstrument import Profiler
        except ImportError:
            logger.warning(
                "pyinstrument not installed — flamegraph disabled. "
                "Install with: pip install pyinstrument"
            )
            yield
            return

        profiler = Profiler()
        profiler.start()
        try:
            yield
        finally:
            profiler.stop()
            timestamp = int(time.time())
            path = self._dir / f"{pipeline}_{timestamp}.html"
            path.write_text(profiler.output_html())
            logger.info(f"Flamegraph saved → {path}")
