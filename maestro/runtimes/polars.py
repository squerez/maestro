from __future__ import annotations

from typing import TYPE_CHECKING, Any, Callable, Dict

from maestro.plugins.plugin import plugin

if TYPE_CHECKING:
    import polars as pl


@plugin(kind="runtime", name="polars")
class PolarsRuntime:
    """
    Polars-based local/in-process runtime.

    Reads and writes via Polars LazyFrames. Suitable for local development,
    testing, and workloads that fit in memory or can be streamed.

    Requires: pip install "maestro[polars]"
    """

    def read(self, source: str, params: Dict[str, Any]) -> "pl.LazyFrame":
        import polars as pl

        fmt = params.get("format", "delta")
        match fmt:
            case "delta":
                return pl.scan_delta(source, **_delta_read_opts(params))
            case "parquet":
                return pl.scan_parquet(source)
            case "csv":
                return pl.scan_csv(source, **params.get("csv_opts", {}))
            case "json" | "ndjson":
                return pl.scan_ndjson(source)
            case _:
                raise ValueError(f"Unsupported format for PolarsRuntime: {fmt!r}")

    def write(self, data: "pl.LazyFrame", destination: str, params: Dict[str, Any]) -> None:
        fmt = params.get("format", "delta")
        mode = params.get("mode", "append")
        match fmt:
            case "delta":
                data.collect().write_delta(
                    destination,
                    mode=mode,
                    delta_write_options=params.get("delta_opts", {}),
                )
            case "parquet":
                data.sink_parquet(destination)
            case "csv":
                data.collect().write_csv(destination)
            case _:
                raise ValueError(f"Unsupported format for PolarsRuntime: {fmt!r}")

    def execute(
        self,
        fn: "Callable[[pl.LazyFrame, Dict[str, Any]], pl.LazyFrame]",
        data: "pl.LazyFrame",
        params: Dict[str, Any],
    ) -> "pl.LazyFrame":
        return fn(data, params)

    def to_pandas(self, data: "pl.LazyFrame | pl.DataFrame") -> "pd.DataFrame":
        import polars as pl

        if isinstance(data, pl.LazyFrame):
            data = data.collect()
        return data.to_pandas()

    def from_pandas(self, df: "pd.DataFrame") -> "pl.LazyFrame":
        import polars as pl

        return pl.from_pandas(df).lazy()


def _delta_read_opts(params: Dict[str, Any]) -> Dict[str, Any]:
    opts: Dict[str, Any] = {}
    if "version" in params:
        opts["version"] = params["version"]
    if "columns" in params:
        opts["columns"] = params["columns"]
    return opts
