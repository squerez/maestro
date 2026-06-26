from maestro.plugins.discovery import discover_plugins
from maestro.plugins.plugin import plugin
from maestro.plugins.registry import PluginRegistry
import maestro.plugins.builtin  # noqa: F401 — registers built-in source/sink plugins

__all__ = ["plugin", "PluginRegistry", "discover_plugins"]
