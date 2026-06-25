from __future__ import annotations

import time
from typing import Optional, Union


class MaestroMetrics:
    def __init__(self) -> None:
        import prometheus_client as prom

        self._runs = prom.Counter(
            "pipeline_runs_total",
            "Total pipeline run completions",
            ["pipeline", "status"],
        )
        self._duration = prom.Histogram(
            "pipeline_duration_seconds",
            "Pipeline run duration in seconds",
            ["pipeline"],
            buckets=[10, 30, 60, 120, 300, 600, 1800],
        )
        self._records = prom.Counter(
            "records_processed_total",
            "Total records processed per step",
            ["pipeline", "step"],
        )
        self._dq_failures = prom.Counter(
            "dq_failures_total",
            "Total data quality failures per suite",
            ["pipeline", "suite"],
        )
        self._sla_breaches = prom.Counter(
            "sla_breaches_total",
            "Total SLA breaches",
            ["pipeline"],
        )
        self._dlq_records = prom.Counter(
            "dlq_records_total",
            "Total records sent to DLQ",
            ["pipeline", "strategy"],
        )

    def record_run_start(self, pipeline: str) -> None:
        pass  # notification only; caller manages its own wall_start timer

    def record_run_end(self, pipeline: str, start: float, status: str) -> None:
        self._duration.labels(pipeline=pipeline).observe(time.time() - start)
        self._runs.labels(pipeline=pipeline, status=status).inc()

    def record_records(self, pipeline: str, step: str, count: int) -> None:
        self._records.labels(pipeline=pipeline, step=step).inc(count)

    def record_dq_failure(self, pipeline: str, suite: str) -> None:
        self._dq_failures.labels(pipeline=pipeline, suite=suite).inc()

    def record_sla_breach(self, pipeline: str) -> None:
        self._sla_breaches.labels(pipeline=pipeline).inc()

    def record_dlq(self, pipeline: str, strategy: str) -> None:
        self._dlq_records.labels(pipeline=pipeline, strategy=strategy).inc()

    def start_http_server(self, port: int) -> None:
        import prometheus_client as prom

        prom.start_http_server(port)


class NullMetrics:
    def record_run_start(self, pipeline: str) -> None: pass
    def record_run_end(self, pipeline: str, start: float, status: str) -> None: pass
    def record_records(self, pipeline: str, step: str, count: int) -> None: pass
    def record_dq_failure(self, pipeline: str, suite: str) -> None: pass
    def record_sla_breach(self, pipeline: str) -> None: pass
    def record_dlq(self, pipeline: str, strategy: str) -> None: pass
    def start_http_server(self, port: int) -> None: pass


_metrics: Union[MaestroMetrics, NullMetrics, None] = None


def get_metrics() -> Union[MaestroMetrics, NullMetrics]:
    global _metrics
    if _metrics is None:
        try:
            _metrics = MaestroMetrics()
        except ImportError:
            _metrics = NullMetrics()
    return _metrics
