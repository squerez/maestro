from __future__ import annotations

import importlib
import pkgutil
from types import ModuleType


def discover_plugins(package: str | ModuleType) -> None:
    """
    Recursively import every module under *package*.

    Importing triggers @plugin decorators, which self-register into
    PluginRegistry. Call once at application startup before executing pipelines.

    Args:
        package: A dotted package name (str) or an already-imported module.
    """
    if isinstance(package, str):
        root = importlib.import_module(package)
    else:
        root = package

    path = getattr(root, "__path__", None)
    if path is None:
        return

    for _finder, name, _is_pkg in pkgutil.walk_packages(
        path=path,
        prefix=root.__name__ + ".",
        onerror=lambda _: None,
    ):
        importlib.import_module(name)
