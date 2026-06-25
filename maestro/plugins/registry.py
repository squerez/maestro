from __future__ import annotations

from typing import Dict, List, Tuple, Type


class PluginRegistry:
    """
    Global registry mapping (kind, name) -> plugin class.

    Populated at import time when @plugin decorators fire during package scanning.
    Raises on collision to catch mis-wiring early.
    """

    _registry: Dict[Tuple[str, str], Type] = {}

    @classmethod
    def register(cls, kind: str, name: str, plugin_cls: Type) -> None:
        key = (kind, name)
        if key in cls._registry:
            existing = cls._registry[key]
            raise ValueError(
                f"Plugin conflict: ({kind!r}, {name!r}) already registered to "
                f"{existing.__qualname__!r}"
            )
        cls._registry[key] = plugin_cls

    @classmethod
    def get(cls, kind: str, name: str) -> Type:
        try:
            return cls._registry[(kind, name)]
        except KeyError:
            raise KeyError(
                f"No plugin registered for kind={kind!r}, name={name!r}"
            )

    @classmethod
    def list_by_kind(cls, kind: str) -> List[str]:
        return [n for k, n in cls._registry if k == kind]

    @classmethod
    def list_kinds(cls) -> List[str]:
        return list({k for k, _ in cls._registry})
