import pytest
from maestro.plugins.plugin import plugin
from maestro.plugins.registry import PluginRegistry


@pytest.fixture(autouse=True)
def clean_registry():
    before = dict(PluginRegistry._registry)
    yield
    PluginRegistry._registry = before


def test_plugin_decorator_registers():
    @plugin(kind="source", name="_test_dec_src")
    class MySource:
        pass

    assert PluginRegistry.get("source", "_test_dec_src") is MySource


def test_plugin_decorator_sets_kind_and_name():
    @plugin(kind="sink", name="_test_dec_sink")
    class MySink:
        pass

    assert MySink._kind == "sink"
    assert MySink._name == "_test_dec_sink"


def test_plugin_decorator_returns_original_class():
    class _Original:
        pass

    decorated = plugin(kind="transform", name="_test_dec_orig")(_Original)
    assert decorated is _Original


def test_plugin_decorator_collision_raises():
    @plugin(kind="source", name="_test_dec_col")
    class First:
        pass

    with pytest.raises(ValueError, match="Plugin conflict"):
        @plugin(kind="source", name="_test_dec_col")
        class Second:
            pass
