from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional

import polars as pl
from loguru import logger

from toolbox.maestro.pipeline.spec import DLQConfig


class DataQualityError(RuntimeError):
    pass


class DLQStrategy(str, Enum):
    SKIP = "skip"
    QUARANTINE = "quarantine"
    FAIL = "fail"


@dataclass
class DLQResult:
    strategy: DLQStrategy
    passed_count: int
    rejected_count: int
    destination: Optional[str]


class DLQRouter:
    def __init__(self, config: DLQConfig) -> None:
        self._config = config

    def route(self, data: pl.DataFrame, failed_mask: pl.Series) -> tuple[pl.DataFrame, DLQResult]:
        config = self._config
        strategy = DLQStrategy(config.strategy)
        failed_count = int(failed_mask.sum())
        clean = data.filter(~failed_mask)

        if strategy is DLQStrategy.FAIL:
            if failed_count > 0:
                raise DataQualityError(f"{failed_count} records failed quality checks")
            return data, DLQResult(
                strategy=strategy,
                passed_count=len(data),
                rejected_count=0,
                destination=None,
            )

        if strategy is DLQStrategy.QUARANTINE:
            if config.destination is None:
                logger.warning(
                    "DLQ strategy is 'quarantine' but no destination is configured; falling back to 'skip'"
                )
                strategy = DLQStrategy.SKIP
            else:
                failed_df = data.filter(failed_mask)
                failed_df.write_parquet(config.destination)
                return clean, DLQResult(
                    strategy=strategy,
                    passed_count=len(clean),
                    rejected_count=failed_count,
                    destination=config.destination,
                )

        # SKIP (or quarantine fallback)
        return clean, DLQResult(
            strategy=strategy,
            passed_count=len(clean),
            rejected_count=failed_count,
            destination=None,
        )
