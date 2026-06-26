import pytest
from maestro.transforms.transform import transform
from maestro.transforms.registry import TransformRegistry


@pytest.fixture(autouse=True)
def clean_registry():
    before = dict(TransformRegistry._registry)
    yield
    TransformRegistry._registry = before


def test_class_transform_registers():
    @transform(name="_test_cls_t", tags=["test"], description="A test transform")
    class MyTransform:
        def run(self, data, params):
            return data

    impl, meta = TransformRegistry.get("_test_cls_t")
    assert meta.name == "_test_cls_t"
    assert "test" in meta.tags
    assert meta.description == "A test transform"


def test_class_transform_returns_original_class():
    class _Original:
        def run(self, data, params):
            return data

    result = transform(name="_test_cls_orig")(_Original)
    assert result is _Original


def test_function_transform_registers():
    @transform(name="_test_fn_t")
    def my_fn(data, params):
        return data

    impl, meta = TransformRegistry.get("_test_fn_t")
    assert meta.name == "_test_fn_t"


def test_function_transform_runs():
    @transform(name="_test_fn_run")
    def double(data, params):
        return data * 2

    impl, _ = TransformRegistry.get("_test_fn_run")
    instance = impl()
    assert instance.run(5, {}) == 10


def test_class_transform_runs():
    @transform(name="_test_cls_run")
    class Uppercase:
        def run(self, data, params):
            return data.upper()

    impl, _ = TransformRegistry.get("_test_cls_run")
    instance = impl()
    assert instance.run("hello", {}) == "HELLO"


def test_collision_raises():
    @transform(name="_test_col_t")
    def first(data, params):
        return data

    with pytest.raises(ValueError, match="already registered"):
        @transform(name="_test_col_t")
        def second(data, params):
            return data


def test_input_schema_stored():
    @transform(
        name="_test_schema_t",
        input_schema=[{"name": "id", "type": "string", "nullable": False}],
    )
    def my_t(data, params):
        return data

    _, meta = TransformRegistry.get("_test_schema_t")
    assert meta.input_schema[0].name == "id"
