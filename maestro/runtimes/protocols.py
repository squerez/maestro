from __future__ import annotations

from typing import Any, Callable, Dict, Protocol, TypeVar

DataFrameT = TypeVar("DataFrameT")


class Runtime(Protocol[DataFrameT]):
    """
    Protocol for data runtimes (Polars, Databricks/Spark).

    Each runtime implementation wraps a specific compute engine and provides
    uniform read/write/execute operations regardless of the underlying engine.
    """

    def read(self, source: str, params: Dict[str, Any]) -> DataFrameT:
        """
        Read a dataset from *source* and return it as the native DataFrame type.

        Args:
            source: A table name, file path, or URI.
            params: Engine-specific options (format, partitions, filters, etc.).
        """

    def write(self, data: DataFrameT, destination: str, params: Dict[str, Any]) -> None:
        """
        Write *data* to *destination*.

        Args:
            data: The native DataFrame produced by a prior step.
            destination: Table name, file path, or URI.
            params: Engine-specific options (mode, partition_by, merge_keys, etc.).
        """

    def execute(
        self,
        fn: Callable[[DataFrameT, Dict[str, Any]], DataFrameT],
        data: DataFrameT,
        params: Dict[str, Any],
    ) -> DataFrameT:
        """
        Apply *fn* to *data* with *params* using the runtime's execution model.

        Args:
            fn: A pure transformation function.
            data: Input DataFrame.
            params: Passed through to *fn*.
        """
