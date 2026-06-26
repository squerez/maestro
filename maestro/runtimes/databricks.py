from __future__ import annotations

from typing import Any, Callable, Dict

from maestro.plugins.plugin import plugin


@plugin(kind="runtime", name="databricks")
class DatabricksRuntime:
    """
    Databricks runtime backed by Databricks Connect (Spark remote execution).

    Requires DATABRICKS_HOST and DATABRICKS_TOKEN env vars, or an explicit
    cluster_id passed via RuntimeConfig.options.
    """

    def __init__(self, cluster_id: str | None = None) -> None:
        self._cluster_id = cluster_id
        self._spark = self._build_session(cluster_id)

    def read(self, source: str, params: Dict[str, Any]) -> Any:
        fmt = params.get("format", "delta")
        reader = self._spark.read.format(fmt)
        for k, v in params.get("options", {}).items():
            reader = reader.option(k, v)
        if fmt == "delta":
            return reader.table(source)
        return reader.load(source)

    def write(self, data: Any, destination: str, params: Dict[str, Any]) -> None:
        fmt = params.get("format", "delta")
        mode = params.get("mode", "append")
        writer = data.write.format(fmt).mode(mode)
        for k, v in params.get("options", {}).items():
            writer = writer.option(k, v)
        if partition_by := params.get("partition_by"):
            writer = writer.partitionBy(*partition_by)
        if fmt == "delta" and params.get("save_as_table"):
            writer.saveAsTable(destination)
        else:
            writer.save(destination)

    def execute(
        self,
        fn: Callable[[Any, Dict[str, Any]], Any],
        data: Any,
        params: Dict[str, Any],
    ) -> Any:
        return fn(data, params)

    def to_pandas(self, data: Any) -> "pd.DataFrame":
        return data.toPandas()

    def from_pandas(self, df: "pd.DataFrame") -> Any:
        return self._spark.createDataFrame(df)

    @staticmethod
    def _build_session(cluster_id: str | None):
        try:
            from databricks.connect import DatabricksSession

            builder = DatabricksSession.builder
            if cluster_id:
                builder = builder.remote(cluster_id=cluster_id)
            return builder.getOrCreate()
        except ImportError:
            raise RuntimeError(
                "databricks-connect is required for DatabricksRuntime. "
                "Install it with: pip install databricks-connect"
            )
