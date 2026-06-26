import textwrap
import pytest
from pathlib import Path

from maestro.pipeline.spec import (
    PipelineSpec,
    StepSpec,
    RuntimeConfig,
    DataContract,
    QualityConfig,
    DLQConfig,
    LineageConfig,
    ObservabilityConfig,
    HandoffConfig,
    ColumnSchema,
)


MINIMAL_DICT = {
    "name": "test_pipeline",
    "steps": [{"name": "ingest", "plugin": "source.http_csv", "params": {"url": "http://x"}}],
}


def test_from_dict_minimal():
    spec = PipelineSpec.from_dict(MINIMAL_DICT)
    assert spec.name == "test_pipeline"
    assert spec.version == "1.0"
    assert len(spec.steps) == 1
    assert spec.steps[0].name == "ingest"
    assert spec.steps[0].plugin == "source.http_csv"


def test_from_dict_defaults():
    spec = PipelineSpec.from_dict(MINIMAL_DICT)
    assert spec.runtime.type == "polars"
    assert spec.dry_run is False
    assert spec.contract is None
    assert spec.quality is None
    assert spec.lineage is None


def test_from_dict_with_contract():
    d = {**MINIMAL_DICT, "contract": {
        "producer": "team/src",
        "consumer": "maestro",
        "version": "2.0",
        "schema": [{"name": "id", "type": "string", "nullable": False}],
    }}
    spec = PipelineSpec.from_dict(d)
    assert spec.contract is not None
    assert spec.contract.producer == "team/src"
    assert spec.contract.schema_[0].name == "id"
    assert spec.contract.schema_[0].nullable is False


def test_from_dict_with_quality():
    d = {**MINIMAL_DICT, "quality": {"suite": "my_suite", "on_failure": "quarantine"}}
    spec = PipelineSpec.from_dict(d)
    assert spec.quality.suite == "my_suite"
    assert spec.quality.on_failure == "quarantine"


def test_from_dict_with_lineage():
    d = {**MINIMAL_DICT, "lineage": {"enabled": True, "backend_url": "http://marquez:5000", "namespace": "ns"}}
    spec = PipelineSpec.from_dict(d)
    assert spec.lineage.enabled is True
    assert spec.lineage.backend_url == "http://marquez:5000"
    assert spec.lineage.namespace == "ns"


def test_from_dict_with_handoff():
    d = {**MINIMAL_DICT, "handoff": {"strategy": "path", "temp_path": "s3://bucket/tmp/", "format": "delta"}}
    spec = PipelineSpec.from_dict(d)
    assert spec.handoff.strategy == "path"
    assert spec.handoff.temp_path == "s3://bucket/tmp/"
    assert spec.handoff.format == "delta"


def test_from_dict_step_on_failure():
    d = {**MINIMAL_DICT}
    d["steps"][0]["on_failure"] = "skip"
    spec = PipelineSpec.from_dict(d)
    assert spec.steps[0].on_failure == "skip"


def test_from_dict_dry_run_flag():
    spec = PipelineSpec.from_dict({**MINIMAL_DICT, "dry_run": True})
    assert spec.dry_run is True


def test_from_dict_multiple_steps():
    d = {
        "name": "multi",
        "steps": [
            {"name": "a", "plugin": "source.http_csv", "params": {}},
            {"name": "b", "plugin": "transform.x", "params": {}},
            {"name": "c", "plugin": "sink.parquet", "params": {"path": "/tmp/out.parquet"}},
        ],
    }
    spec = PipelineSpec.from_dict(d)
    assert [s.name for s in spec.steps] == ["a", "b", "c"]


def test_from_yaml(tmp_path):
    yaml_content = textwrap.dedent("""\
        name: yaml_pipeline
        version: "2.0"
        runtime:
          type: polars
        steps:
          - name: load
            plugin: source.http_csv
            params:
              url: http://example.com/data.csv
    """)
    f = tmp_path / "pipeline.yaml"
    f.write_text(yaml_content)
    spec = PipelineSpec.from_yaml(f)
    assert spec.name == "yaml_pipeline"
    assert spec.version == "2.0"
    assert spec.steps[0].plugin == "source.http_csv"


def test_from_yaml_missing_file():
    with pytest.raises(FileNotFoundError):
        PipelineSpec.from_yaml("/nonexistent/path/pipeline.yaml")


def test_runtime_config_databricks():
    d = {**MINIMAL_DICT, "runtime": {"type": "databricks", "options": {"cluster_id": "abc"}}}
    spec = PipelineSpec.from_dict(d)
    assert spec.runtime.type == "databricks"
    assert spec.runtime.options["cluster_id"] == "abc"


def test_quality_on_failure_defaults_to_fail():
    config = QualityConfig(suite="s")
    assert config.on_failure == "fail"


def test_dlq_strategy_defaults_to_quarantine():
    config = DLQConfig()
    assert config.strategy == "quarantine"


def test_handoff_defaults():
    config = HandoffConfig()
    assert config.strategy == "auto"
    assert config.format == "parquet"
    assert config.temp_path is None


def test_lineage_defaults():
    config = LineageConfig()
    assert config.enabled is True
    assert config.namespace == "maestro"
    assert config.backend_url is None
