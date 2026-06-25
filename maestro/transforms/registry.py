from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple, Type, Union

from toolbox.maestro.pipeline.spec import ColumnSchema


@dataclass
class TransformMeta:
    name: str
    tags: List[str] = field(default_factory=list)
    input_schema: List[ColumnSchema] = field(default_factory=list)
    output_schema: List[ColumnSchema] = field(default_factory=list)
    description: str = ""


_TransformImpl = Union[Type, Callable]


class TransformRegistry:
    """
    Registry of named, reusable transforms.

    Keyed by name. Each entry stores the implementation (class or function)
    and associated metadata (tags, input/output schemas, description).
    """

    _registry: Dict[str, Tuple[_TransformImpl, TransformMeta]] = {}

    @classmethod
    def register(cls, name: str, impl: _TransformImpl, meta: TransformMeta) -> None:
        if name in cls._registry:
            existing = cls._registry[name][0]
            raise ValueError(
                f"Transform {name!r} already registered to "
                f"{getattr(existing, '__qualname__', repr(existing))!r}"
            )
        cls._registry[name] = (impl, meta)

    @classmethod
    def get(cls, name: str) -> Tuple[_TransformImpl, TransformMeta]:
        try:
            return cls._registry[name]
        except KeyError:
            raise KeyError(f"No transform registered with name={name!r}")

    @classmethod
    def list_all(cls) -> List[TransformMeta]:
        return [meta for _, meta in cls._registry.values()]

    @classmethod
    def list_by_tag(cls, tag: str) -> List[TransformMeta]:
        return [meta for _, meta in cls._registry.values() if tag in meta.tags]

    @classmethod
    def validate_input(cls, name: str, data: Any) -> List[str]:
        """
        Return column-level violations against the registered input schema.

        Works on Polars DataFrame, LazyFrame (via .schema), or any object
        with a .schema or .columns attribute.
        """
        _, meta = cls.get(name)
        if not meta.input_schema:
            return []

        available: set[str] = set()
        if hasattr(data, "schema"):
            available = set(data.schema.names() if callable(getattr(data.schema, "names", None)) else data.schema)
        elif hasattr(data, "columns"):
            available = set(data.columns)

        return [
            f"missing column {col.name!r} (expected type {col.type!r})"
            for col in meta.input_schema
            if col.name not in available
        ]
