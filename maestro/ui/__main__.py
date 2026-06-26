import os

from maestro.ui.app import serve

serve(
    host=os.environ.get("MAESTRO_HOST", "0.0.0.0"),
    port=int(os.environ.get("MAESTRO_PORT", "8080")),
    checkpoint_dir=os.environ.get("MAESTRO_CHECKPOINT_DIR", "~/.maestro/checkpoints"),
    grafana_url=os.environ.get("GRAFANA_URL") or None,
    lineage_url=os.environ.get("LINEAGE_URL") or None,
    ge_docs_dir=os.environ.get("GE_DOCS_DIR") or None,
)
