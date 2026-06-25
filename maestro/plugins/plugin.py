from __future__ import annotations

from toolbox.maestro.plugins.registry import PluginRegistry


def plugin(kind: str, name: str):
    """
    Class decorator that registers a plugin into PluginRegistry.

    Usage:
        @plugin(kind="source", name="delta")
        class DeltaSourcePlugin:
            def __init__(self, runtime, params): ...

    Args:
        kind: Plugin category — "source", "sink", "transform", "quality",
              "lineage", or "runtime".
        name: Unique name within the kind, e.g. "delta", "great_expectations".
    """

    def decorator(cls):
        cls._kind = kind
        cls._name = name
        PluginRegistry.register(kind, name, cls)
        return cls

    return decorator
