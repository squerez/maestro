from toolbox.maestro.plugins.discovery import discover_plugins
from toolbox.maestro.plugins.plugin import plugin
from toolbox.maestro.plugins.registry import PluginRegistry
import toolbox.maestro.plugins.builtin  # noqa: F401 — registers built-in source/sink plugins

__all__ = ["plugin", "PluginRegistry", "discover_plugins"]
