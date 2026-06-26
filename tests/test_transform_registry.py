import pytest
from maestro.transforms.registry import TransformRegistry, TransformMeta
from maestro.pipeline.spec import ColumnSchema


@pytest.fixture(autouse=True)
def clean_registry():
    before = dict(TransformRegistry._registry)
    yield
    TransformRegistry._registry = before


class _DummyTransform:
    def run(self, data, params):
        return data


def _meta(name="t", tags=None, input_schema=None, output_schema=None):
    return TransformMeta(
        name=name,
        tags=tags or [],
        input_schema=input_schema or [],
        output_schema=output_schema or [],
    )


def test_register_and_get():
    meta = _meta("_test_t1")
    TransformRegistry.register("_test_t1", _DummyTransform, meta)
    impl, retrieved_meta = TransformRegistry.get("_test_t1")
    assert impl is _DummyTransform
    assert retrieved_meta.name == "_test_t1"


def test_get_missing_raises():
    with pytest.raises(KeyError, match="No transform registered"):
        TransformRegistry.get("_nonexistent_transform")


def test_register_collision_raises():
    meta = _meta("_test_col")
    TransformRegistry.register("_test_col", _DummyTransform, meta)
    with pytest.raises(ValueError, match="already registered"):
        TransformRegistry.register("_test_col", _DummyTransform, meta)


def test_list_all():
    m1 = _meta("_test_la1")
    m2 = _meta("_test_la2")
    TransformRegistry.register("_test_la1", _DummyTransform, m1)
    TransformRegistry.register("_test_la2", _DummyTransform, m2)
    names = [m.name for m in TransformRegistry.list_all()]
    assert "_test_la1" in names
    assert "_test_la2" in names


def test_list_by_tag():
    m1 = _meta("_test_tag1", tags=["cleaning"])
    m2 = _meta("_test_tag2", tags=["enrichment"])
    m3 = _meta("_test_tag3", tags=["cleaning", "enrichment"])
    TransformRegistry.register("_test_tag1", _DummyTransform, m1)
    TransformRegistry.register("_test_tag2", _DummyTransform, m2)
    TransformRegistry.register("_test_tag3", _DummyTransform, m3)

    cleaning = [m.name for m in TransformRegistry.list_by_tag("cleaning")]
    assert "_test_tag1" in cleaning
    assert "_test_tag3" in cleaning
    assert "_test_tag2" not in cleaning


def test_validate_input_no_schema():
    meta = _meta("_test_vi_none")
    TransformRegistry.register("_test_vi_none", _DummyTransform, meta)
    violations = TransformRegistry.validate_input("_test_vi_none", object())
    assert violations == []


def test_validate_input_all_present():
    schema = [ColumnSchema(name="id", type="string"), ColumnSchema(name="val", type="float")]
    meta = TransformMeta(name="_test_vi_ok", input_schema=schema)
    TransformRegistry.register("_test_vi_ok", _DummyTransform, meta)

    class _FakeData:
        columns = ["id", "val", "extra"]

    violations = TransformRegistry.validate_input("_test_vi_ok", _FakeData())
    assert violations == []


def test_validate_input_missing_column():
    schema = [ColumnSchema(name="id", type="string"), ColumnSchema(name="missing_col", type="int")]
    meta = TransformMeta(name="_test_vi_miss", input_schema=schema)
    TransformRegistry.register("_test_vi_miss", _DummyTransform, meta)

    class _FakeData:
        columns = ["id"]

    violations = TransformRegistry.validate_input("_test_vi_miss", _FakeData())
    assert len(violations) == 1
    assert "missing_col" in violations[0]
