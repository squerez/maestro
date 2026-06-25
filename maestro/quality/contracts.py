from __future__ import annotations

from dataclasses import dataclass, field

import polars as pl

from toolbox.maestro.pipeline.spec import DataContract

_POLARS_TYPE_MAP: dict[str, pl.PolarsDataType] = {
    "string": pl.Utf8,
    "int": pl.Int64,
    "float": pl.Float64,
    "double": pl.Float64,
    "boolean": pl.Boolean,
    "date": pl.Date,
    "datetime": pl.Datetime,
    "binary": pl.Binary,
}


@dataclass
class ContractViolations:
    valid: bool
    missing_columns: list[str]
    type_mismatches: list[tuple[str, str, str]]
    nullability_violations: list[str]


class ContractValidator:
    def validate(self, data: pl.DataFrame, contract: DataContract) -> ContractViolations:
        actual_columns = set(data.columns)
        schema_map = {col.name: col for col in contract.schema_}

        missing = [name for name in schema_map if name not in actual_columns]

        type_mismatches: list[tuple[str, str, str]] = []
        nullability_violations: list[str] = []

        for col in contract.schema_:
            if col.name in missing:
                continue

            expected_dtype = _POLARS_TYPE_MAP.get(col.type)
            if expected_dtype is not None:
                actual_dtype = data[col.name].dtype
                if actual_dtype != expected_dtype:
                    type_mismatches.append((col.name, col.type, str(actual_dtype)))

            if not col.nullable and data[col.name].null_count() > 0:
                nullability_violations.append(col.name)

        return ContractViolations(
            valid=not (missing or type_mismatches or nullability_violations),
            missing_columns=missing,
            type_mismatches=type_mismatches,
            nullability_violations=nullability_violations,
        )
