from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone


@dataclass
class PipelineEvent:
    event_type: str
    pipeline: str
    timestamp: str
    payload: dict


class EventLogger:
    def __init__(self, destination: str | None = None) -> None:
        self._destination = destination

    @staticmethod
    def now() -> str:
        return datetime.now(timezone.utc).isoformat()

    def emit(self, event: PipelineEvent) -> None:
        from loguru import logger

        logger.debug("pipeline_event type={} pipeline={}", event.event_type, event.pipeline)

        if self._destination is None:
            return

        if self._destination.startswith("http"):
            try:
                import requests

                requests.post(self._destination, json=asdict(event), timeout=5)
            except Exception as exc:
                logger.warning("EventLogger HTTP emit failed: {}", exc)
        else:
            with open(self._destination, "a") as fh:
                fh.write(json.dumps(asdict(event)) + "\n")

    def pipeline_start(self, pipeline: str, spec_version: str) -> None:
        self.emit(
            PipelineEvent(
                event_type="pipeline_start",
                pipeline=pipeline,
                timestamp=self.now(),
                payload={"spec_version": spec_version},
            )
        )

    def pipeline_end(
        self,
        pipeline: str,
        status: str,
        duration_seconds: float,
        records: int,
    ) -> None:
        self.emit(
            PipelineEvent(
                event_type="pipeline_end",
                pipeline=pipeline,
                timestamp=self.now(),
                payload={
                    "status": status,
                    "duration_seconds": duration_seconds,
                    "records": records,
                },
            )
        )

    def step_start(self, pipeline: str, step: str) -> None:
        self.emit(
            PipelineEvent(
                event_type="step_start",
                pipeline=pipeline,
                timestamp=self.now(),
                payload={"step": step},
            )
        )

    def step_end(
        self,
        pipeline: str,
        step: str,
        records: int,
        duration_seconds: float,
    ) -> None:
        self.emit(
            PipelineEvent(
                event_type="step_end",
                pipeline=pipeline,
                timestamp=self.now(),
                payload={"step": step, "records": records, "duration_seconds": duration_seconds},
            )
        )

    def dq_result(
        self,
        pipeline: str,
        suite: str,
        success: bool,
        failed_count: int,
    ) -> None:
        self.emit(
            PipelineEvent(
                event_type="dq_result",
                pipeline=pipeline,
                timestamp=self.now(),
                payload={"suite": suite, "success": success, "failed_count": failed_count},
            )
        )

    def sla_breach(
        self,
        pipeline: str,
        duration_minutes: float,
        limit_minutes: int,
    ) -> None:
        self.emit(
            PipelineEvent(
                event_type="sla_breach",
                pipeline=pipeline,
                timestamp=self.now(),
                payload={
                    "duration_minutes": duration_minutes,
                    "limit_minutes": limit_minutes,
                },
            )
        )
