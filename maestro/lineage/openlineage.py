from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from loguru import logger

from maestro.pipeline.spec import LineageConfig, PipelineSpec


@dataclass
class DatasetRef:
    name: str
    namespace: str | None = None


def datasets_from_spec(
    spec: PipelineSpec,
    emitter_namespace: str,
) -> tuple[list[DatasetRef], list[DatasetRef]]:
    inputs: list[DatasetRef] = []
    outputs: list[DatasetRef] = []

    for step in spec.steps:
        ref_name = step.params.get("table") or step.params.get("path")
        if ref_name is None:
            continue
        ref = DatasetRef(name=str(ref_name), namespace=emitter_namespace)
        if step.plugin.startswith("source."):
            inputs.append(ref)
        elif step.plugin.startswith("sink."):
            outputs.append(ref)

    return inputs, outputs


def new_run_id() -> str:
    try:
        from openlineage.client.uuid import generate_new_uuid
        return str(generate_new_uuid())
    except ModuleNotFoundError:
        import uuid
        return str(uuid.uuid4())


class OpenLineageEmitter:
    def __init__(self, config: LineageConfig) -> None:
        self._client = None
        self._namespace = config.namespace

        if not config.enabled:
            return

        try:
            from openlineage.client import OpenLineageClient

            if config.backend_url:
                self._client = OpenLineageClient(url=config.backend_url)
            else:
                self._client = OpenLineageClient.from_environment()
        except Exception as exc:
            logger.warning("openlineage-python unavailable, lineage emission disabled: {}", exc)

    def _emit(self, event: object) -> None:
        try:
            self._client.emit(event)  # type: ignore[union-attr]
        except Exception as exc:
            logger.warning("Failed to emit OpenLineage event: {}", exc)

    def _build_event(
        self,
        event_type: object,
        pipeline: str,
        run_id: str,
        inputs: list[DatasetRef],
        outputs: list[DatasetRef],
        run_facets: dict | None = None,
    ) -> object:
        from openlineage.client.generated.base import (
            InputDataset,
            Job,
            OutputDataset,
            Run,
            RunEvent,
        )

        run_kwargs: dict = {"runId": run_id}
        if run_facets:
            run_kwargs["facets"] = run_facets

        return RunEvent(
            eventType=event_type,
            eventTime=datetime.now(tz=timezone.utc).isoformat(),
            run=Run(**run_kwargs),
            job=Job(namespace=self._namespace, name=pipeline),
            inputs=[
                InputDataset(
                    namespace=r.namespace if r.namespace is not None else self._namespace,
                    name=r.name,
                )
                for r in inputs
            ],
            outputs=[
                OutputDataset(
                    namespace=r.namespace if r.namespace is not None else self._namespace,
                    name=r.name,
                )
                for r in outputs
            ],
        )

    def start(
        self,
        pipeline: str,
        run_id: str,
        inputs: list[DatasetRef],
        outputs: list[DatasetRef],
    ) -> None:
        if self._client is None:
            return
        from openlineage.client.generated.base import EventType

        self._emit(self._build_event(EventType.START, pipeline, run_id, inputs, outputs))

    def complete(
        self,
        pipeline: str,
        run_id: str,
        inputs: list[DatasetRef],
        outputs: list[DatasetRef],
    ) -> None:
        if self._client is None:
            return
        from openlineage.client.generated.base import EventType

        self._emit(self._build_event(EventType.COMPLETE, pipeline, run_id, inputs, outputs))

    def fail(
        self,
        pipeline: str,
        run_id: str,
        error: str,
        inputs: list[DatasetRef],
        outputs: list[DatasetRef],
    ) -> None:
        if self._client is None:
            return
        from openlineage.client.generated.base import EventType

        run_facets: dict | None = None
        try:
            from openlineage.client.generated.error_message_run import ErrorMessageRunFacet

            run_facets = {"errorMessage": ErrorMessageRunFacet(message=error, programmingLanguage="python")}
        except Exception:
            pass

        self._emit(self._build_event(EventType.FAIL, pipeline, run_id, inputs, outputs, run_facets))
