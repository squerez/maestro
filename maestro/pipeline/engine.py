from __future__ import annotations

import json
import time
import uuid
from contextlib import nullcontext
from typing import Any, Dict, List, Optional

from loguru import logger

from maestro.pipeline.dryrun import DryRunResult, StepDryRunResult
from maestro.pipeline.spec import HandoffConfig, PipelineSpec, RuntimeConfig, StepSpec
from maestro.pipeline.state import Checkpoint, CheckpointStore
from maestro.plugins.discovery import discover_plugins
from maestro.plugins.registry import PluginRegistry


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
        # Keyed by (runtime_type, json-serialised options) so the same Databricks
        # session is reused across steps rather than reconnected on each one.
        self._runtime_cache: Dict[tuple, Any] = {}

    def run(
        self,
        spec: PipelineSpec,
        *,
        dry_run: Optional[bool] = None,
    ) -> Optional[DryRunResult]:
        """
        Execute the pipeline described by *spec*.

        Steps may each declare their own runtime override; the engine handles
        cross-runtime data handoff automatically (pandas bridge or path-based).

        Args:
            spec: The pipeline specification.
            dry_run: Override ``spec.dry_run``. When True, sink steps are
                     skipped and a DryRunResult is returned instead of None.
        """
        is_dry_run = dry_run if dry_run is not None else spec.dry_run

        for pkg in self._plugin_packages:
            discover_plugins(pkg)

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

        sla_ctx = self._build_sla_ctx(spec, metrics, event_logger)
        flamegraph_ctx = self._build_flamegraph_ctx(spec)

        current_data: Any = None
        current_runtime: Any = None
        total_records = 0
        step_results: List[StepDryRunResult] = []
        run_metadata: Dict[str, Any] = {}

        with flamegraph_ctx:
            with sla_ctx:
                try:
                    for step in spec.steps:
                        step_start = time.monotonic()
                        kind = step.plugin.split(".", 1)[0]
                        is_sink = kind == "sink"

                        step_runtime = self._get_or_build_runtime(step.runtime or spec.runtime)
                        runtime_type = type(step_runtime).__name__

                        # Cross-runtime handoff when the step switches engines.
                        if current_data is not None and current_runtime is not step_runtime:
                            current_data = self._handoff(
                                data=current_data,
                                from_runtime=current_runtime,
                                to_runtime=step_runtime,
                                handoff_cfg=spec.handoff,
                                pipeline=spec.name,
                                step_name=step.name,
                                is_dry_run=is_dry_run,
                            )

                        event_logger.step_start(spec.name, step.name)
                        logger.info(
                            f"[{spec.name}] step={step.name} plugin={step.plugin}"
                            f" runtime={runtime_type}"
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
                                    runtime_type=runtime_type,
                                    skipped=True,
                                )
                            )
                            event_logger.step_end(spec.name, step.name, records_out, step_dur)
                            current_runtime = step_runtime
                            continue

                        current_data = self._execute_step(
                            step=step,
                            runtime=step_runtime,
                            data=current_data,
                            spec=spec,
                            metrics=metrics,
                            event_logger=event_logger,
                            run_metadata=run_metadata,
                        )
                        current_runtime = step_runtime

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
                                    runtime_type=runtime_type,
                                    preview=preview,
                                )
                            )

                    if not is_dry_run:
                        if spec.observability and spec.observability.grafana_url:
                            run_metadata["grafana_url"] = spec.observability.grafana_url
                        self._store.save(
                            Checkpoint(
                                pipeline=spec.name,
                                last_run=CheckpointStore.now(),
                                status="success",
                                records_processed=total_records,
                                extra=run_metadata,
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
        run_metadata: Optional[Dict[str, Any]] = None,
    ) -> Any:
        kind, name = step.plugin.split(".", 1)

        # "quality" and "transform" bypass PluginRegistry because they carry
        # engine-level context (spec, metrics, event_logger) that the generic
        # plugin interface does not expose.
        if kind == "quality":
            from maestro.quality.runner import run_quality_step

            data_out, dq_result = run_quality_step(
                data=data,
                quality_cfg=spec.quality,
                dlq_cfg=spec.dlq,
                step=step,
                metrics=metrics,
                event_logger=event_logger,
                pipeline=spec.name,
            )
            if dq_result is not None and run_metadata is not None:
                run_metadata.setdefault("dq_results", {})[dq_result.suite] = {
                    "success": dq_result.success,
                    "statistics": dq_result.statistics,
                    "failed_expectations": dq_result.failed_expectations,
                }
            return data_out

        if kind == "transform":
            return self._execute_transform_step(step, data)

        plugin_cls = PluginRegistry.get(kind, name)
        return plugin_cls(runtime=runtime).run(data, step.params)

    def _execute_transform_step(self, step: StepSpec, data: Any) -> Any:
        from maestro.transforms.registry import TransformRegistry

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
    # Runtime management
    # ------------------------------------------------------------------

    def _get_or_build_runtime(self, config: RuntimeConfig) -> Any:
        cache_key = (config.type, json.dumps(config.options, sort_keys=True, default=str))
        if cache_key not in self._runtime_cache:
            self._runtime_cache[cache_key] = self._build_runtime(config)
        return self._runtime_cache[cache_key]

    def _build_runtime(self, config: RuntimeConfig) -> Any:
        runtime_cls = PluginRegistry.get("runtime", config.type)
        return runtime_cls(**config.options)

    # ------------------------------------------------------------------
    # Cross-runtime handoff
    # ------------------------------------------------------------------

    def _handoff(
        self,
        data: Any,
        from_runtime: Any,
        to_runtime: Any,
        handoff_cfg: Optional[HandoffConfig],
        pipeline: str,
        step_name: str,
        is_dry_run: bool = False,
    ) -> Any:
        from_type = type(from_runtime).__name__
        to_type = type(to_runtime).__name__
        logger.info(
            f"[{pipeline}] crossing runtime boundary: {from_type} → {to_type}"
            f" (before step {step_name!r})"
        )

        strategy = handoff_cfg.strategy if handoff_cfg else "auto"

        if strategy in ("auto", "memory"):
            try:
                return self._bridge_via_pandas(data, from_runtime, to_runtime)
            except MemoryError as exc:
                if strategy == "memory":
                    raise
                logger.warning(
                    f"[{pipeline}] in-memory bridge failed ({exc}),"
                    " falling back to path handoff"
                )

        # Path-based handoff: write to temp storage, read back with the other runtime.
        if is_dry_run:
            logger.info(
                f"[{pipeline}] DRY RUN — skipping path handoff, passing data through"
            )
            return data

        if not handoff_cfg or not handoff_cfg.temp_path:
            raise RuntimeError(
                "Cross-runtime path handoff requires handoff.temp_path in the pipeline spec.\n"
                "Example:\n"
                "  handoff:\n"
                "    strategy: path\n"
                "    temp_path: s3://my-bucket/maestro-tmp/\n"
                "    format: parquet"
            )

        return self._bridge_via_path(
            data, from_runtime, to_runtime, handoff_cfg, pipeline, step_name
        )

    def _bridge_via_pandas(self, data: Any, from_runtime: Any, to_runtime: Any) -> Any:
        pandas_df = from_runtime.to_pandas(data)
        return to_runtime.from_pandas(pandas_df)

    def _bridge_via_path(
        self,
        data: Any,
        from_runtime: Any,
        to_runtime: Any,
        handoff_cfg: HandoffConfig,
        pipeline: str,
        step_name: str,
    ) -> Any:
        temp_path = (
            f"{handoff_cfg.temp_path.rstrip('/')}"
            f"/{pipeline}/{step_name}/{uuid.uuid4().hex}"
        )
        fmt = handoff_cfg.format
        logger.debug(f"[{pipeline}] handoff write → {temp_path} ({fmt})")
        from_runtime.write(data, temp_path, {"format": fmt})
        logger.debug(f"[{pipeline}] handoff read ← {temp_path} ({fmt})")
        return to_runtime.read(temp_path, {"format": fmt})

    # ------------------------------------------------------------------
    # Context builders
    # ------------------------------------------------------------------

    def _init_observability(self, spec: PipelineSpec):
        from maestro.observability.events import EventLogger
        from maestro.observability.metrics import get_metrics

        metrics = get_metrics()
        destination = spec.observability.event_log if spec.observability else None
        return metrics, EventLogger(destination)

    def _init_lineage(self, spec: PipelineSpec):
        if not spec.lineage or not spec.lineage.enabled:
            return None, "", [], []

        from maestro.lineage.openlineage import (
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
            from maestro.observability.sla import SLATracker

            return SLATracker(spec.name, spec.observability.sla, metrics, event_logger)
        return nullcontext()

    def _build_flamegraph_ctx(self, spec: PipelineSpec):
        if spec.observability and spec.observability.flamegraph_dir:
            from maestro.observability.flamegraph import PipelineProfiler

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
