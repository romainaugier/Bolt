import textwrap

import pytest

from bolt.core.errors import PluginError
from bolt.core.registry import Registry

auto_plugin = """
import bolt

vector_type = bolt.DataType("vector3", tuple, default=(0.0, 0.0, 0.0))

class Length(bolt.Node):
    type_name = "geo.length"
    inputs = (bolt.Input("vector", "vector3"),)
    outputs = (bolt.Output("length", "float"),)

    def cook(self, ctx):
        ctx.set("length", sum(component ** 2 for component in ctx.get("vector")) ** 0.5)

class _Helper(bolt.Node):
    pass
"""

explicit_plugin = """
import bolt

class Hidden(bolt.Node):
    type_name = "explicit.hidden"

class Shown(bolt.Node):
    type_name = "explicit.shown"

def register(registry):
    registry.register_node(Shown)
"""


def write(path, text):
    path.write_text(textwrap.dedent(text))
    return path


def test_auto_registration_from_file(tmp_path):
    registry = Registry()
    registry.load_plugin(write(tmp_path / "geometry.py", auto_plugin))
    assert registry.has_node_type("geo.length")
    assert registry.data_type("vector3").default() == (0.0, 0.0, 0.0)
    assert "bolt_plugin_geometry" in registry.plugins


def test_register_function_takes_precedence(tmp_path):
    registry = Registry()
    registry.load_plugin(str(write(tmp_path / "explicit.py", explicit_plugin)))
    assert registry.has_node_type("explicit.shown")
    assert not registry.has_node_type("explicit.hidden")


def test_package_plugin_with_relative_imports(tmp_path):
    package = tmp_path / "toolkit"
    package.mkdir()
    write(package / "nodes.py", """
        import bolt

        class Hello(bolt.Node):
            type_name = "toolkit.hello"
            outputs = (bolt.Output("text", "string"),)

            def cook(self, ctx):
                ctx.set("text", "hello")
    """)
    write(package / "__init__.py", """
        from . import nodes

        def register(registry):
            registry.register_module(nodes)
    """)
    registry = Registry()
    registry.load_plugin(package)
    assert registry.has_node_type("toolkit.hello")


def test_discovery_collects_errors(tmp_path, monkeypatch):
    plugins = tmp_path / "plugins"
    plugins.mkdir()
    write(plugins / "good.py", auto_plugin)
    write(plugins / "broken.py", "raise RuntimeError('broken plugin')")
    write(plugins / "_private.py", "raise RuntimeError('never imported')")
    other = tmp_path / "other"
    other.mkdir()
    write(other / "explicit.py", explicit_plugin)
    monkeypatch.setenv("BOLT_PLUGIN_PATH", str(other))

    registry = Registry()
    errors = registry.discover_plugins([plugins, tmp_path / "does_not_exist"], entry_point_group=None)
    assert registry.has_node_type("geo.length")
    assert registry.has_node_type("explicit.shown")
    messages = [str(error) for error in errors]
    assert len(messages) == 2
    assert any("broken plugin" in message for message in messages)
    assert any("does not exist" in message for message in messages)


def test_failing_register_raises(tmp_path):
    registry = Registry()
    with pytest.raises(PluginError, match="failed to register"):
        registry.load_plugin(write(tmp_path / "bad.py", "def register(registry):\n    raise ValueError('nope')\n"))


def test_unknown_module_raises():
    with pytest.raises(PluginError):
        Registry().load_plugin("bolt_no_such_plugin_module")


def test_registries_are_independent(tmp_path):
    first = Registry()
    second = Registry()
    first.load_plugin(write(tmp_path / "geometry.py", auto_plugin))
    assert first.has_node_type("geo.length")
    assert not second.has_node_type("geo.length")
    core_only = Registry(core=False)
    assert not core_only.node_classes() and not core_only.data_types()
