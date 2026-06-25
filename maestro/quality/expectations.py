from __future__ import annotations

from dataclasses import dataclass, field

import polars as pl

from toolbox.maestro.pipeline.spec import QualityConfig


@dataclass
class GXValidationResult:
    success: bool
    suite: str
    statistics: dict
    failed_expectations: list[str]


class GXValidator:
    def __init__(self, context_root: str | None = None) -> None:
        import great_expectations as gx

        if context_root is not None:
            self._context = gx.get_context(mode="file", project_root_dir=context_root)
        else:
            self._context = gx.get_context(mode="ephemeral")

    def validate(self, data: pl.DataFrame, config: QualityConfig) -> GXValidationResult:
        context = self._context

        datasource = context.sources.add_or_update_pandas(name="maestro")
        asset = datasource.add_dataframe_asset(name="dataset")
        batch_request = asset.build_batch_request(dataframe=data.to_pandas())

        try:
            results = context.run_checkpoint(
                checkpoint_name=config.suite,
                validations=[{"batch_request": batch_request}],
            )
        except Exception as exc:
            raise ValueError(
                f"GE checkpoint {config.suite!r} not found or failed to run: {exc}"
            ) from exc

        run_result = list(results.run_results.values())[0]
        validation_result = run_result["validation_result"]
        statistics = dict(validation_result.statistics)

        failed = [
            str(r.expectation_config.expectation_type)
            for r in validation_result.results
            if not r.success
        ]

        return GXValidationResult(
            success=bool(results.success),
            suite=config.suite,
            statistics=statistics,
            failed_expectations=failed,
        )
