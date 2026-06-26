from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Literal, Optional

import yaml
from pydantic import BaseModel, Field


class ColumnSchema(BaseModel):
    name: str
    type: str
    nullable: bool = True


class DataContract(BaseModel):
    schema_: List[ColumnSchema] = Field(default_factory=list, alias="schema")
    producer: str
    consumer: str
    version: str = "1.0"

    model_config = {"populate_by_name": True}


class SLAConfig(BaseModel):
    max_duration_minutes: int
    alert_channel: Optional[str] = None


class QualityConfig(BaseModel):
    suite: str
    datasource: Optional[str] = None
    on_failure: Literal["skip", "quarantine", "fail"] = "fail"


class DLQConfig(BaseModel):
    strategy: Literal["skip", "quarantine", "fail"] = "quarantine"
    destination: Optional[str] = None


class LineageConfig(BaseModel):
    enabled: bool = True
    backend_url: Optional[str] = None
    namespace: str = "maestro"


class ObservabilityConfig(BaseModel):
    prometheus_port: Optional[int] = 8000
    event_log: Optional[str] = None
    sla: Optional[SLAConfig] = None
    flamegraph_dir: Optional[str] = None
    grafana_url: Optional[str] = None


class RuntimeConfig(BaseModel):
    type: Literal["polars", "databricks"] = "polars"
    options: Dict[str, Any] = Field(default_factory=dict)


class HandoffConfig(BaseModel):
    """
    Controls how data is transferred when consecutive steps run on different runtimes.

    strategy:
      auto   — try in-memory pandas bridge first; fall back to path on MemoryError
      memory — always use pandas bridge; fail if data does not fit
      path   — always write to temp_path and read back (requires temp_path)

    temp_path: cloud URI used for path-based handoff, e.g.
      s3://my-bucket/maestro-tmp/
      abfss://container@account.dfs.core.windows.net/maestro-tmp/
    """

    strategy: Literal["auto", "memory", "path"] = "auto"
    temp_path: Optional[str] = None
    format: Literal["parquet", "delta"] = "parquet"


class StepSpec(BaseModel):
    name: str
    plugin: str
    params: Dict[str, Any] = Field(default_factory=dict)
    on_failure: Optional[Literal["skip", "quarantine", "fail"]] = None
    runtime: Optional[RuntimeConfig] = None


class PipelineSpec(BaseModel):
    name: str
    version: str = "1.0"
    schedule: Optional[str] = None
    runtime: RuntimeConfig = Field(default_factory=RuntimeConfig)
    contract: Optional[DataContract] = None
    quality: Optional[QualityConfig] = None
    dlq: Optional[DLQConfig] = None
    lineage: Optional[LineageConfig] = None
    observability: Optional[ObservabilityConfig] = None
    handoff: Optional[HandoffConfig] = None
    steps: List[StepSpec] = Field(default_factory=list)
    dry_run: bool = False
    preview_rows: int = 5

    @classmethod
    def from_yaml(cls, path: str | Path) -> "PipelineSpec":
        with open(path) as f:
            data = yaml.safe_load(f)
        return cls.model_validate(data)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PipelineSpec":
        return cls.model_validate(data)
