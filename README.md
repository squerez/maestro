# maestro

A metadata-driven data engineering framework with a plugin registry, observability, data quality, and lineage tracking.

## Overview

Maestro runs data pipelines defined as YAML specs. Each pipeline is a sequence of steps executed by a plugin — sources pull data in, transforms reshape it, sinks write it out. The engine handles runtimes, cross-runtime handoffs, quality checks, lineage emission, and metrics automatically.

```
YAML spec → PipelineEngine → [source] → [transform…] → [sink]
                 │
                 ├── Polars / Databricks runtime
                 ├── Great Expectations quality checks
                 ├── OpenLineage / Marquez lineage
                 └── Prometheus metrics + event log
```

## Quick start

### Local

```sh
# install
uv sync

# run a pipeline
uv run python -c "from maestro.main import run; run('examples/ai_career_threat.yaml')"

# or via make
make run-pipeline PIPELINE=examples/ai_career_threat.yaml
```

### Docker Compose

```sh
# UI only
make docker-up

# UI + Prometheus + Grafana
make docker-up-obs

# UI + Marquez lineage
make docker-up-lineage

# everything
make docker-up-all
```

| Service       | URL                     |
|---------------|-------------------------|
| Maestro UI    | http://localhost:8080   |
| Grafana       | http://localhost:3000   |
| Prometheus    | http://localhost:9090   |
| Marquez API   | http://localhost:5000   |
| Marquez Web   | http://localhost:3001   |

## Pipeline spec

Pipelines are YAML files. Every field except `name` and `steps` is optional.

```yaml
name: my_pipeline
version: "1.0"

# Runtime — polars (default) or databricks
runtime:
  type: polars

# Data contract — validated after the final step
contract:
  producer: "team/source"
  consumer: "maestro"
  version: "1.0"
  schema:
    - {name: id,    type: string, nullable: false}
    - {name: value, type: float,  nullable: true}

# Great Expectations quality gate
quality:
  suite: my_suite
  on_failure: fail   # skip | quarantine | fail

# Dead-letter queue for bad records
dlq:
  strategy: quarantine
  destination: /tmp/dlq/

# OpenLineage / Marquez
lineage:
  enabled: true
  backend_url: http://localhost:5000
  namespace: my-team

# Prometheus + event log
observability:
  event_log: /tmp/maestro/events.jsonl
  grafana_url: http://localhost:3000/d/maestro-pipelines-v1/maestro-pipelines

# Cross-runtime data handoff
handoff:
  strategy: auto    # auto | memory | path
  temp_path: s3://bucket/maestro-tmp/
  format: parquet   # parquet | delta

steps:
  - name: ingest
    plugin: source.http_json
    params:
      url: https://api.example.com/data
      list_key: items

  - name: clean
    plugin: transform.my_transform
    params: {}

  - name: write
    plugin: sink.parquet
    params:
      path: /tmp/output/data.parquet
```

### Step `on_failure`

Each step can override the pipeline-level failure strategy:

```yaml
steps:
  - name: risky_step
    plugin: source.http_json
    on_failure: skip   # skip | quarantine | fail
    params: {}
```

## Built-in plugins

### Sources

| Plugin | Description | Key params |
|--------|-------------|------------|
| `source.http_csv` | Download CSV from URL | `url`, `separator` |
| `source.http_json` | Fetch JSON API, extract list | `url`, `list_key`, `query_params`, `headers` |
| `source.http_ndjson` | Download newline-delimited JSON | `url` |
| `source.local_zip_csv` | Read CSV from local zip | `path`, `csv_name`, `separator` |
| `source.kaggle_zip_csv` | Download Kaggle dataset zip + read CSV | `dataset`, `csv_name`, `cache_dir` |

### Sinks

| Plugin | Description | Key params |
|--------|-------------|------------|
| `sink.parquet` | Write Parquet file | `path`, `compression` |
| `sink.csv` | Write CSV file | `path`, `separator` |

## Writing a plugin

Decorate any class with `@plugin(kind, name)`. The class must implement `run(self, data, params) -> data`.

```python
from maestro.plugins.plugin import plugin

@plugin(kind="source", name="my_source")
class MySourcePlugin:
    def __init__(self, runtime=None) -> None:
        pass

    def run(self, data, params):
        import polars as pl
        return pl.DataFrame({"col": [1, 2, 3]}).lazy()
```

Plugins are auto-discovered from packages listed in `MaestroConfig.plugin_packages`. Point it at your package and all `@plugin`-decorated classes are registered.

```python
from maestro.config import MaestroConfig
from maestro.main import run

run("my_pipeline.yaml", config=MaestroConfig(plugin_packages=["mypackage.plugins"]))
```

## Writing a transform

Use `@transform` for reusable, named data transformations. Supports both class and function forms.

```python
from maestro.transforms.transform import transform

@transform(name="drop_nulls", tags=["cleaning"], description="Drop rows with any null")
def drop_nulls(data, params):
    return data.drop_nulls()
```

Reference in YAML as `plugin: transform.drop_nulls`.

## Runtimes

| Runtime | YAML value | Notes |
|---------|-----------|-------|
| Polars | `polars` | Default. LazyFrame throughout. |
| Databricks | `databricks` | Requires `databricks-sdk` + `databricks-connect` extras. |

Steps can switch runtimes mid-pipeline. The engine bridges data automatically via the `handoff` config.

## Observability

### Prometheus metrics

Set `observability.prometheus_port` in the spec to expose a `/metrics` endpoint, or run the UI which exposes metrics at `/metrics` by default.

Grafana dashboard at `grafana/maestro_dashboard.json` is auto-provisioned when using Docker Compose.

### Event log

Set `observability.event_log` to a file path. The engine appends JSONL events (`pipeline_start`, `step_start`, `step_end`, `pipeline_end`) on each run.

### SLA monitoring

```yaml
observability:
  sla:
    max_duration_minutes: 30
    alert_channel: "#data-alerts"
```

## Data quality

Maestro integrates Great Expectations. Point `quality.suite` at a checkpoint name in your GX project.

```yaml
quality:
  suite: my_checkpoint
  on_failure: quarantine
```

The GX context root defaults to `<checkpoint_dir>/ge`. Data Docs are served by the UI at `/quality/docs` when `GE_DOCS_DIR` is set.

## Lineage

Maestro emits OpenLineage events to a Marquez backend.

```yaml
lineage:
  enabled: true
  backend_url: http://marquez:5000
  namespace: my-team
```

If `openlineage-python` is not installed, emission is silently skipped and run IDs fall back to stdlib `uuid`.

## Configuration

`MaestroConfig` controls host-level defaults (all per-pipeline settings live in the YAML spec):

```python
from maestro.config import MaestroConfig

cfg = MaestroConfig(
    checkpoint_dir="~/.maestro/checkpoints",
    plugin_packages=["mypackage.plugins", "mypackage.transforms"],
    default_runtime="polars",
)
```

Environment variables used by the UI container:

| Variable | Default | Description |
|----------|---------|-------------|
| `MAESTRO_HOST` | `0.0.0.0` | Bind address |
| `MAESTRO_PORT` | `8080` | HTTP port |
| `MAESTRO_CHECKPOINT_DIR` | `~/.maestro/checkpoints` | Checkpoint storage |
| `GRAFANA_URL` | — | Grafana link shown in the UI |
| `LINEAGE_URL` | — | Marquez Web link shown in the UI |
| `GE_DOCS_DIR` | — | Directory to serve as GX Data Docs |

## Development

```sh
# install with dev dependencies
make install-dev

# run tests
make test

# run tests with coverage
make test-cov

# lint / format
make lint
make format

# dry-run a pipeline (no sinks executed)
make dry-run PIPELINE=examples/ai_career_threat.yaml
```

### Extras

```sh
uv sync --extra ui           # FastAPI UI
uv sync --extra observability # Prometheus + pyinstrument
uv sync --extra lineage      # openlineage-python
uv sync --extra quality      # great-expectations
uv sync --extra polars        # polars
uv sync --extra databricks   # databricks-sdk + databricks-connect
uv sync --all-extras          # everything
```

## Examples

| File | Description |
|------|-------------|
| `examples/ai_career_threat.yaml` | Fetches AI career threat index CSV, enriches, writes Parquet |
| `examples/eonet_events.yaml` | NASA EONET natural events API → Parquet |
| `examples/celeba_attributes.yaml` | CelebA dataset from Kaggle → Parquet |
