import pytest


@pytest.fixture(autouse=False)
def clean_plugin_registry():
    from maestro.plugins.registry import PluginRegistry
    before = dict(PluginRegistry._registry)
    yield
    PluginRegistry._registry = before


@pytest.fixture(autouse=False)
def clean_transform_registry():
    from maestro.transforms.registry import TransformRegistry
    before = dict(TransformRegistry._registry)
    yield
    TransformRegistry._registry = before
