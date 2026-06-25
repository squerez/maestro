from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional, Type, Union

from toolbox.maestro.pipeline.spec import ColumnSchema
from toolbox.maestro.transforms.registry import TransformMeta, TransformRegistry


def transform(
    name: str,
    tags: Optional[List[str]] = None,
    input_schema: Optional[List[Dict[str, Any]]] = None,
    output_schema: Optional[List[Dict[str, Any]]] = None,
    description: str = "",
):
    """
    Class or function decorator registering a reusable, named transform.

    Transforms are discoverable via TransformRegistry and executable as
    pipeline steps using ``plugin: "transform.<name>"``.

    Class usage — must implement ``run(self, data, params) -> data``:

        @transform(name="drop_nulls", tags=["cleaning"])
        class DropNullsTransform:
            def run(self, data: pl.LazyFrame, params: dict) -> pl.LazyFrame:
                return data.drop_nulls()

    Function usage — signature ``fn(data, params) -> data``:

        @transform(name="drop_nulls", tags=["cleaning"])
        def drop_nulls(data: pl.LazyFrame, params: dict) -> pl.LazyFrame:
            return data.drop_nulls()
    """
    in_schema = [ColumnSchema(**c) for c in (input_schema or [])]
    out_schema = [ColumnSchema(**c) for c in (output_schema or [])]
    meta = TransformMeta(
        name=name,
        tags=tags or [],
        input_schema=in_schema,
        output_schema=out_schema,
        description=description,
    )

    def decorator(fn_or_cls: Union[Type, Callable]) -> Union[Type, Callable]:
        if isinstance(fn_or_cls, type):
            plugin_cls = fn_or_cls
        else:
            fn = fn_or_cls

            class _FnAdapter:
                _kind = "transform"
                _name = name

                def __init__(self, runtime: Any = None) -> None:
                    pass

                def run(self, data: Any, params: Dict[str, Any]) -> Any:
                    return fn(data, params)

            _FnAdapter.__name__ = getattr(fn, "__name__", name)
            _FnAdapter.__qualname__ = getattr(fn, "__qualname__", name)
            plugin_cls = _FnAdapter

        plugin_cls._transform_meta = meta
        TransformRegistry.register(name, plugin_cls, meta)
        return fn_or_cls

    return decorator
