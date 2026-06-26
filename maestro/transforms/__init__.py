from maestro.transforms.registry import TransformMeta, TransformRegistry
from maestro.transforms.transform import transform

# Built-in transforms are registered when discover_plugins("maestro.transforms")
# runs at engine startup (included in MaestroConfig.plugin_packages by default).
# Eager imports here are intentionally removed: career/celeba/eonet have a
# hard top-level polars dependency that would break `import maestro` for users
# who haven't installed the polars extra.

__all__ = ["transform", "TransformRegistry", "TransformMeta"]
