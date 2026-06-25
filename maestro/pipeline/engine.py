from __future__ import annotations

import time
from contextlib import nullcontext
from typing import Any, Dict, List, Optional

from loguru import logger

from toolbox.maestro.pipeline.dryrun import DryRunResult, StepDryRunResult
from toolbox.maestro.pipeline.spec import PipelineSpec, RuntimeConfig, StepSpec
from toolbox.maestro.pipeline.state import Checkpoint, CheckpointStore
from toolbox.maestro.plugins.discovery import discover_plugins
from toolbox.maestro.plugins.registry import PluginRegistry


class PipelineEngine:
    """
    Orchestrates pipeline execution: runtimes, steps, quality, transforms,
    lineage, observability, dry-run, and flamegraph profiling.
    """

    def __init__(
        self,
        checkpoint_store: Optional[CheckpointStore] = None,
        plugin_packages: Optional[List[str]] = None,
    ) -> None:
        self._store = checkpoint_store or CheckpointStore()
        self._plugin_packages = plugin_packages or []

    def run(
        self,
        spec: PipelineSpec,
        *,
        dry_run: Optional[bool] = None,
    ) -> Optional[DryRunResult]:
        """
        Execute the pipeline described by *spec*.

        Args:
            spec: The pipeline specification.
            dry_run: Override ``spec.dry_run``. When True, sink steps are
                     skipped and a DryRunResult is returned instead of None.
        """
        is_dry_run = dry_run if dry_run is not None else spec.dry_run

        for pkg in self._plugin_packages:
            discover_plugins(pkg)

        runtime = self._build_runtime(spec.runtime)
        metrics, event_logger = self._init_observability(spec)
        lineage, run_id, inputs, outputs = self._init_lineage(spec)

        if spec.observability and spec.observability.prometheus_port:
            metrics.start_http_server(spec.observability.prometheus_port)

        if is_dry_run:
            logger.info(f"[{spec.name}] DRY RUN — sink steps will be skipped")

        event_logger.pipeline_start(spec.name, spec.version)
        wall_start = time.time()
        metrics.record_run_start(spec.name)

        if lineage and not is_dry_run:
            lineage.start(spec.name, run_id, inputs, outputs)

        checkpoint = self._store.load(spec.name)
        sla_ctx = self._build_sla_ctx(spec, metrics, event_logger)
        flamegraph_ctx = self._build_flamegraph_ctx(spec)

        current_data: Any = None
        total_records = 0
        step_results: List[StepDryRunResult] = []

        with flamegraph_ctx:
            with sla_ctx:
                try:
                    for step in spec.steps:
                        step_start = time.monotonic()
                        kind = step.plugin.split(".", 1)[0]
                        is_sink = kind == "sink"

                        event_logger.step_start(spec.name, step.name)
                        logger.info(
                            f"[{spec.name}] step={step.name} plugin={step.plugin}"
                            + (" [DRY RUN SKIP]" if is_dry_run and is_sink else "")
                        )

                        records_in = _count_records(current_data)

                        if is_dry_run and is_sink:
                            records_out = records_in
                            step_dur = time.monotonic() - step_start
                            step_results.append(
                                StepDryRunResult(
                                    name=step.name,
                                    plugin=step.plugin,
                                    records_in=records_in,
                                    records_out=records_out,
                                    duration_seconds=step_dur,
                                    skipped=True,
                                )
                            )
                            event_logger.step_end(spec.name, step.name, records_out, step_dur)
                            continue

                        current_data = self._execute_step(
                            step=step,
                            runtime=runtime,
                            data=current_data,
                            spec=spec,
                            metrics=metrics,
                            event_logger=event_logger,
                        )

                        records_out = _count_records(current_data)
                        total_records += records_out
                        metrics.record_records(spec.name, step.name, records_out)
                        step_dur = time.monotonic() - step_start
                        event_logger.step_end(spec.name, step.name, records_out, step_dur)

                        if is_dry_run:
                            preview = _preview(current_data, spec.preview_rows)
                            step_results.append(
                                StepDryRunResult(
                                    name=step.name,
                                    plugin=step.plugin,
                                    records_in=records_in,
                                    records_out=records_out,
                                    duration_seconds=step_dur,
                                    preview=preview,
                                )
                            )

                    if not is_dry_run:
                        extra = {}
                        if spec.observability and spec.observability.grafana_url:
                            extra["grafana_url"] = spec.observability.grafana_url
                        self._store.save(
                            Checkpoint(
                                pipeline=spec.name,
                                last_run=CheckpointStore.now(),
                                status="success",
                                records_processed=total_records,
                                extra=extra,
                            )
                        )

                    total_dur = time.time() - wall_start
                    event_logger.pipeline_end(spec.name, "success", total_dur, total_records)
                    metrics.record_run_end(spec.name, wall_start, "success")

                    if lineage and not is_dry_run:
                        lineage.complete(spec.name, run_id, inputs, outputs)

                    logger.info(
                        f"[{spec.name}] {'dry-run' if is_dry_run else 'completed'} "
                        f"records={total_records} duration={total_dur:.1f}s"
                    )

                    if is_dry_run:
                        result = DryRunResult(
                            pipeline=spec.name,
                            total_duration_seconds=total_dur,
                            step_results=step_results,
                        )
                        logger.info("\n" + result.summary())
                        return result

                    return None

                except Exception as exc:
                    self._store.save(
                        Checkpoint(
                            pipeline=spec.name,
                            last_run=CheckpointStore.now(),
                            status="failed",
                        )
                    )
                    total_dur = time.time() - wall_start
                    event_logger.pipeline_end(spec.name, "failed", total_dur, total_records)
                    metrics.record_run_end(spec.name, wall_start, "failed")

                    if lineage and not is_dry_run:
                        lineage.fail(spec.name, run_id, str(exc), inputs, outputs)

                    logger.error(f"[{spec.name}] failed after {total_dur:.1f}s: {exc}")
                    raise

    # ------------------------------------------------------------------
    # Step dispatch
    # ------------------------------------------------------------------

    def _execute_step(
        self,
        step: StepSpec,
        runtime: Any,
        data: Any,
        spec: PipelineSpec,
        metrics: Any,
        event_logger: Any,
    ) -> Any:
        kind, name = step.plugin.split(".", 1)

        # "quality" and "transform" are built-in lifecycle kinds dispatched
        # directly to their dedicated handlers rather than through PluginRegistry.
        # This is intentional: they carry engine-level context (spec, metrics,
        # event_logger) that the generic plugin interface does not expose.
        if kind == "quality":
            return self._execute_quality_step(step, data, spec, metrics, event_logger)

        if kind == "transform":
            return self._execute_transform_step(step, data)

        plugin_cls = PluginRegistry.get(kind, name)
        instance = plugin_cls(runtime=runtime)
        return instance.run(data, step.params)

    def _execute_quality_step(
        self,
        step: StepSpec,
        data: Any,
        spec: PipelineSpec,
        metrics: Any,
        event_logger: Any,
    ) -> Any:
        from toolbox.maestro.quality.dlq import DataQualityError, DLQRouter
        from toolbox.maestro.quality.expectations import GXValidator

        quality_cfg = spec.quality
        if quality_cfg is None:
            return data

        df = _to_eager(data)
        validator = GXValidator()
        result = validator.validate(df, quality_cfg)

        event_logger.dq_result(
            spec.name, quality_cfg.suite, result.success, len(result.failed_expectations)
        )

        if not result.success:
            metrics.record_dq_failure(spec.name, quality_cfg.suite)
            logger.warning(
                f"[{spec.name}] DQ failed suite={quality_cfg.suite!r} "
                f"failed={result.failed_expectations}"
            )

            if spec.dlq:
                import polars as pl

                router = DLQRouter(spec.dlq)
                failed_mask = pl.Series([True] * len(df))
                clean_df, dlq_result = router.route(df, failed_mask)
                metrics.record_dlq(spec.name, dlq_result.strategy.value)
                return clean_df

            on_failure = step.on_failure or quality_cfg.on_failure
            if on_failure == "fail":
                raise DataQualityError(
                    f"Quality gate failed for suite {quality_cfg.suite!r}"
                )

        return data

    def _execute_transform_step(self, step: StepSpec, data: Any) -> Any:
        from toolbox.maestro.transforms.registry import TransformRegistry

        _, name = step.plugin.split(".", 1)
        plugin_cls, meta = TransformRegistry.get(name)

        if meta.input_schema:
            violations = TransformRegistry.validate_input(name, data)
            if violations:
                logger.warning(
                    f"Transform {name!r} input schema violations: {violations}"
                )

        instance = plugin_cls()
        return instance.run(data, step.params)

    # ------------------------------------------------------------------
    # Context builders
    # ------------------------------------------------------------------

    def _build_runtime(self, config: RuntimeConfig) -> Any:
        runtime_cls = PluginRegistry.get("runtime", config.type)
        return runtime_cls(**config.options)

    def _init_observability(self, spec: PipelineSpec):
        from toolbox.maestro.observability.events import EventLogger
        from toolbox.maestro.observability.metrics import get_metrics

        metrics = get_metrics()
        destination = spec.observability.event_log if spec.observability else None
        return metrics, EventLogger(destination)

    def _init_lineage(self, spec: PipelineSpec):
        if not spec.lineage or not spec.lineage.enabled:
            return None, "", [], []

        from toolbox.maestro.lineage.openlineage import (
            OpenLineageEmitter,
            datasets_from_spec,
            new_run_id,
        )

        emitter = OpenLineageEmitter(spec.lineage)
        run_id = new_run_id()
        inputs, outputs = datasets_from_spec(spec, spec.lineage.namespace)
        return emitter, run_id, inputs, outputs

    def _build_sla_ctx(self, spec: PipelineSpec, metrics: Any, event_logger: Any):
        if spec.observability and spec.observability.sla:
            from toolbox.maestro.observability.sla import SLATracker

            return SLATracker(spec.name, spec.observability.sla, metrics, event_logger)
        return nullcontext()

    def _build_flamegraph_ctx(self, spec: PipelineSpec):
        if spec.observability and spec.observability.flamegraph_dir:
            from toolbox.maestro.observability.flamegraph import PipelineProfiler

            return PipelineProfiler(spec.observability.flamegraph_dir).profile(spec.name)
        return nullcontext()


# ------------------------------------------------------------------
# Utilities
# ------------------------------------------------------------------

def _to_eager(data: Any) -> Any:
    try:
        import polars as pl

        if isinstance(data, pl.LazyFrame):
            return data.collect()
    except ImportError:
        pass
    return data


def _count_records(data: Any) -> int:
    if data is None:
        return 0
    try:
        return len(data)
    except TypeError:
        return 0


def _preview(data: Any, n: int) -> Optional[Any]:
    if data is None or n <= 0:
        return None
    try:
        eager = _to_eager(data)
        return eager.head(n) if hasattr(eager, "head") else None
    except Exception:
        return None
