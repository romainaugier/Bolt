from __future__ import annotations

import pytest

from bolt.core.graph import Graph
from bolt.core.registry import Registry
from support import cooks, test_nodes


@pytest.fixture(autouse=True)
def _reset_cooks():
    cooks.clear()
    yield
    cooks.clear()


@pytest.fixture
def registry() -> Registry:
    registry = Registry()
    for node_class in test_nodes:
        registry.register_node(node_class)
    return registry


@pytest.fixture
def graph(registry: Registry) -> Graph:
    return Graph(registry)
