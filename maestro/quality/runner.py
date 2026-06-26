from __future__ import annotations

from typing import Any, Optional

from loguru import logger

from maestro.pipeline.spec import DLQConfig, QualityConfig, StepSpec
from maestro.quality.expectations import GXValidationResult


def run_quality_step(
    data: Any,
    quality_cfg: Optional[QualityConfig],
    dlq_cfg: Optional[DLQConfig],
    step: StepSpec,
    metrics: Any,
    event_logger: Any,
    pipeline: str,
) -> tuple[Any, Optional[GXValidationResult]]:
    """
    Run GX validation and optional DLQ routing for a quality step.

    Returns the (possibly filtered) data and the validation result.
    The caller is responsible for persisting the result if needed.
    """
    if quality_cfg is None:
        return data, None

    from maestro.quality.dlq import DataQualityError, DLQRouter
    from maestro.quality.expectations import GXValidator

    df = _to_eager(data)
    result = GXValidator().validate(df, quality_cfg)

    event_logger.dq_result(
        pipeline, quality_cfg.suite, result.success, len(result.failed_expectations)
    )

    if not result.success:
        metrics.record_dq_failure(pipeline, quality_cfg.suite)
        logger.warning(
            "[{}] DQ failed suite={!r} failed={}",
            pipeline,
            quality_cfg.suite,
            result.failed_expectations,
        )

        if dlq_cfg:
            failed_mask = _row_mask(df, result.failed_row_indices)
            clean_df, dlq_result = DLQRouter(dlq_cfg).route(df, failed_mask)
            metrics.record_dlq(pipeline, dlq_result.strategy.value)
            return clean_df, result

        on_failure = step.on_failure or quality_cfg.on_failure
        if on_failure == "fail":
            raise DataQualityError(
                f"Quality gate failed for suite {quality_cfg.suite!r}"
            )

    return data, result


def _to_eager(data: Any) -> Any:
    try:
        import polars as pl

        if isinstance(data, pl.LazyFrame):
            return data.collect()
    except ImportError:
        pass
    return data


def _row_mask(df: Any, failed_indices: list[int]) -> Any:
    import polars as pl

    row_idx = pl.Series("idx", range(len(df)), dtype=pl.Int64)
    return row_idx.is_in(failed_indices)
