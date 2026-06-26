import pytest
from maestro.plugins.registry import PluginRegistry


@pytest.fixture(autouse=True)
def clean_plugin_registry():
    before = dict(PluginRegistry._registry)
    yield
    PluginRegistry._registry = before


class _DummyPlugin:
    pass


class _OtherPlugin:
    pass


def test_register_and_get():
    PluginRegistry.register("source", "_test_dummy", _DummyPlugin)
    assert PluginRegistry.get("source", "_test_dummy") is _DummyPlugin


def test_get_missing_raises():
    with pytest.raises(KeyError, match="No plugin registered"):
        PluginRegistry.get("source", "_nonexistent")


def test_register_collision_raises():
    PluginRegistry.register("source", "_test_col", _DummyPlugin)
    with pytest.raises(ValueError, match="Plugin conflict"):
        PluginRegistry.register("source", "_test_col", _OtherPlugin)


def test_same_name_different_kind_allowed():
    PluginRegistry.register("source", "_test_shared", _DummyPlugin)
    PluginRegistry.register("sink", "_test_shared", _OtherPlugin)
    assert PluginRegistry.get("source", "_test_shared") is _DummyPlugin
    assert PluginRegistry.get("sink", "_test_shared") is _OtherPlugin


def test_list_by_kind():
    PluginRegistry.register("source", "_test_a", _DummyPlugin)
    PluginRegistry.register("source", "_test_b", _OtherPlugin)
    PluginRegistry.register("sink", "_test_c", _DummyPlugin)
    names = PluginRegistry.list_by_kind("source")
    assert "_test_a" in names
    assert "_test_b" in names
    assert "_test_c" not in names


def test_list_kinds():
    PluginRegistry.register("source", "_test_k1", _DummyPlugin)
    PluginRegistry.register("transform", "_test_k2", _OtherPlugin)
    kinds = PluginRegistry.list_kinds()
    assert "source" in kinds
    assert "transform" in kinds
