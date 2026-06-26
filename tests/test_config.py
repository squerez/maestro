from maestro.config import MaestroConfig


def test_defaults():
    cfg = MaestroConfig()
    assert cfg.checkpoint_dir == "~/.maestro/checkpoints"
    assert cfg.default_runtime == "polars"
    assert "maestro.plugins" in cfg.plugin_packages
    assert "maestro.transforms" in cfg.plugin_packages
    assert "maestro.runtimes" in cfg.plugin_packages


def test_custom_checkpoint_dir():
    cfg = MaestroConfig(checkpoint_dir="/tmp/custom")
    assert cfg.checkpoint_dir == "/tmp/custom"


def test_custom_plugin_packages():
    cfg = MaestroConfig(plugin_packages=["mypkg.plugins"])
    assert cfg.plugin_packages == ["mypkg.plugins"]


def test_instances_are_independent():
    a = MaestroConfig(checkpoint_dir="/a")
    b = MaestroConfig(checkpoint_dir="/b")
    assert a.checkpoint_dir != b.checkpoint_dir
