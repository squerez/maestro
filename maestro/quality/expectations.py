from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from maestro.pipeline.spec import QualityConfig

if TYPE_CHECKING:
    import polars as pl


@dataclass
class GXValidationResult:
    success: bool
    suite: str
    statistics: dict
    failed_expectations: list[str]
    failed_row_indices: list[int] = field(default_factory=list)


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
                validations=[{
                    "batch_request": batch_request,
                    "result_format": {"result_format": "COMPLETE"},
                }],
            )
        except Exception as exc:
            raise ValueError(
                f"GE checkpoint {config.suite!r} not found or failed to run: {exc}"
            ) from exc

        run_result = list(results.run_results.values())[0]
        validation_result = run_result["validation_result"]
        statistics = dict(validation_result.statistics)

        failed: list[str] = []
        failed_indices: set[int] = set()
        for r in validation_result.results:
            if not r.success:
                failed.append(str(r.expectation_config.expectation_type))
                for idx in r.result.get("unexpected_index_list", []):
                    failed_indices.add(int(idx))

        return GXValidationResult(
            success=bool(results.success),
            suite=config.suite,
            statistics=statistics,
            failed_expectations=failed,
            failed_row_indices=sorted(failed_indices),
        )
