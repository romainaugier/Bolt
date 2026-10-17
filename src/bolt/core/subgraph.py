from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any

from bolt.core.changes import ChangeKind
from bolt.core.errors import Cancelled, CookError, GraphError
from bolt.core.expressions import missing
from bolt.core.graph import Graph
from bolt.core.node import Node, NodeState
from bolt.core.plugs import Input, Output, Plug, PlugKind, PlugSpec, unset
from bolt.core.datatypes import DataType

if TYPE_CHECKING:
    from bolt.core.evaluation import CookContext, Evaluation


class GraphInput(Node):
    type_name = "bolt.graph_input"
    category = "Graph"
    ui = {"style": "subgraph", "icon": "login"}
    description = "Exposes the inputs of the owning subgraph node inside the subgraph."
    removable = False

    def cook(self, ctx: CookContext) -> None:
        pass


class GraphOutput(Node):
    type_name = "bolt.graph_output"
    category = "Graph"
    ui = {"style": "subgraph", "icon": "logout"}
    description = "Collects the values returned by the owning subgraph node."
    removable = False

    def __init__(self, name: str | None = None) -> None:
        super().__init__(name)
        self.values: dict[str, Any] = {}

    def cook(self, ctx: CookContext) -> None:
        self.values = {plug.name: ctx.get(plug.name) for plug in self.declared_plugs(PlugKind.input)}


def _same(a: Any, b: Any) -> bool:
    if a is b:
        return True

    if type(a) is not type(b) or type(a) not in (int, float, str, bool, bytes):
        return False

    return a == b


class SubgraphNode(Node):
    """A node whose cook evaluates a nested graph. Its dynamic plugs mirror the inner graph_input/graph_output nodes."""

    type_name = "bolt.subgraph"
    category = "Graph"
    ui = {"style": "subgraph", "icon": "deployed_code"}
    description = "Groups nodes into a reusable nested graph."

    input_node_name = "inputs"
    output_node_name = "outputs"
    user_plugs = True

    def __init__(self, name: str | None = None) -> None:
        super().__init__(name)
        self.subgraph: Graph | None = None

    @property
    def input_node(self) -> GraphInput:
        return self._inner().node(self.input_node_name)

    @property
    def output_node(self) -> GraphOutput:
        return self._inner().node(self.output_node_name)

    def child_graphs(self) -> tuple[Graph, ...]:
        return (self.subgraph,) if self.subgraph is not None else ()

    def on_attached(self) -> None:
        if self.subgraph is None:
            self.subgraph = self.create_subgraph()

    def create_subgraph(self) -> Graph:
        graph = self.graph
        subgraph = Graph(graph.registry, name=self.name, events=graph.events, owner=self)
        subgraph.add_node(GraphInput(self.input_node_name), unique=False)
        subgraph.add_node(GraphOutput(self.output_node_name), unique=False)

        return subgraph

    def add_subgraph_input(self, name: str, data_type: str | DataType = "any", default: Any = None) -> Plug:
        plug = self.add_plug(Input(name, data_type, default))
        self.input_node.add_plug(Output(name, data_type))

        return plug

    def remove_subgraph_input(self, name: str) -> None:
        self.remove_plug(name)
        self.input_node.remove_plug(name)

    def add_subgraph_output(self, name: str, data_type: str | DataType = "any") -> Plug:
        plug = self.add_plug(Output(name, data_type))
        self.output_node.add_plug(Input(name, data_type))

        return plug

    def remove_subgraph_output(self, name: str) -> None:
        self.remove_plug(name)
        self.output_node.remove_plug(name)

    def add_user_plug(self, spec: PlugSpec) -> Plug:
        if spec.kind is PlugKind.input:
            return self.add_subgraph_input(spec.name, spec.data_type, spec.default)

        if spec.kind is PlugKind.output:
            return self.add_subgraph_output(spec.name, spec.data_type)

        return super().add_user_plug(spec)

    def remove_user_plug(self, name: str) -> None:
        kind = self.plug(name).spec.kind

        if kind is PlugKind.input:
            self.remove_subgraph_input(name)
        elif kind is PlugKind.output:
            self.remove_subgraph_output(name)
        else:
            super().remove_user_plug(name)

    def has_internal_changes(self, evaluation: Evaluation, since: int) -> bool:
        for node in self._inner().walk():
            if node._modified_at > since:
                return True

            if node._snapshot:
                variables = evaluation.variables_for(node.graph)

                for name, value in node._snapshot.items():
                    if variables.get(name, missing) != value:
                        return True

        return False

    def cook(self, ctx: CookContext) -> None:
        self.feed_inputs({plug.name: self.incoming(ctx, plug.name) for plug in self.declared_plugs(PlugKind.input)})
        self.run_subgraph(ctx)

        values = self.output_node.values

        for plug in self.output_plugs():
            ctx.set(plug.name, values.get(plug.name))

    def incoming(self, ctx: CookContext, name: str) -> tuple[Any, Any]:
        if self.input_node.plug(name).tracked:
            change = ctx.change(name)
            return change.value, change.delta if change.kind is ChangeKind.delta else unset

        return ctx.get(name), unset

    def feed_inputs(self, values: Mapping[str, tuple[Any, Any]], *, always: bool = False) -> None:
        input_node = self.input_node
        changed = always or input_node.state is not NodeState.cooked

        for name, (value, delta) in values.items():
            plug = input_node.plug(name)

            if delta is unset and _same(plug.value, value):
                continue

            plug.publish(value, delta)
            changed = True

        if changed:
            input_node._mark_cooked()

    def run_subgraph(self, ctx: CookContext, label: str = "") -> None:
        result = ctx.evaluation.child(self._inner()).execute(self.output_node)

        if result.cancelled:
            raise Cancelled("evaluation cancelled")

        if not result.succeeded:
            prefix = f"{label}: " if label else ""

            if result.failed:
                node, error = next(iter(result.failed.items()))
                raise CookError(f"{prefix}{node.path} failed: {error}")

            raise CookError(f"{prefix}subgraph evaluation failed")

    def save_extra(self) -> dict[str, Any] | None:
        from bolt.core.serialization import graph_to_dict

        return {"graph": graph_to_dict(self._inner())}

    def load_extra(self, data: Mapping[str, Any]) -> None:
        from bolt.core.serialization import graph_from_dict

        graph_data = data.get("graph")

        if graph_data is not None:
            self.subgraph = graph_from_dict(graph_data, self.graph.registry, owner=self, events=self.graph.events)

    def _inner(self) -> Graph:
        if self.subgraph is None:
            raise GraphError(f"subgraph node {self.path} must be added to a graph first")

        return self.subgraph


class ForEachNode(SubgraphNode):
    """Evaluates its subgraph once per item of the 'items' list and gathers each 'result' into 'results'."""

    type_name = "bolt.for_each"
    ui = {"style": "loop", "icon": "repeat"}
    description = "Runs the nested graph once for every item of a list."
    inputs = (Input("items", "list"),)
    outputs = (Output("results", "list"),)

    def create_subgraph(self) -> Graph:
        subgraph = super().create_subgraph()
        input_node = subgraph.node(self.input_node_name)
        input_node.add_plug(Output("item", "any"))
        input_node.add_plug(Output("index", "int"))
        subgraph.node(self.output_node_name).add_plug(Input("result", "any"))

        return subgraph

    def cook(self, ctx: CookContext) -> None:
        items = ctx.get("items")
        extra = {plug.name: self.incoming(ctx, plug.name)
                 for plug in self.declared_plugs(PlugKind.input) if plug.dynamic}
        results = []
        count = len(items)

        for index, item in enumerate(items):
            ctx.checkpoint()
            self.feed_inputs({**extra, "item": (item, unset), "index": (index, unset)}, always=True)
            self.run_subgraph(ctx, f"iteration {index}")
            results.append(self.output_node.values.get("result"))
            ctx.progress((index + 1) / count)

        ctx.set("results", results)
