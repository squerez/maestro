from __future__ import annotations

import time
from typing import Optional

from maestro.pipeline.spec import SLAConfig

from .events import EventLogger
from .metrics import MaestroMetrics, NullMetrics


class SLATracker:
    def __init__(
        self,
        pipeline: str,
        config: SLAConfig,
        metrics: MaestroMetrics | NullMetrics | None = None,
        event_logger: EventLogger | None = None,
    ) -> None:
        self._pipeline = pipeline
        self._config = config
        self._metrics = metrics
        self._event_logger = event_logger
        self._start: Optional[float] = None

    @property
    def elapsed_seconds(self) -> float:
        if self._start is None:
            raise RuntimeError("SLATracker has not been entered yet")
        return time.monotonic() - self._start

    def __enter__(self) -> SLATracker:
        self._start = time.monotonic()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        from loguru import logger

        elapsed_s = self.elapsed_seconds
        elapsed_m = elapsed_s / 60.0
        limit_m = self._config.max_duration_minutes

        if elapsed_m > limit_m:
            channel_info = f" (channel={self._config.alert_channel})" if self._config.alert_channel else ""
            logger.warning(
                "SLA breach for pipeline '{}': {:.2f}m elapsed, limit {}m{}",
                self._pipeline,
                elapsed_m,
                limit_m,
                channel_info,
            )

            if self._metrics is not None:  # None only when explicitly passed by tests
                self._metrics.record_sla_breach(self._pipeline)

            if self._event_logger is not None:
                self._event_logger.sla_breach(
                    pipeline=self._pipeline,
                    duration_minutes=elapsed_m,
                    limit_minutes=limit_m,
                )

        return None
