"""Sugiyama layered layout for node graphs flowing left to right.

The function only sees boxes and edges, so any front end can use it: give it each node's size, the edges with the
vertical offset of their ports inside the nodes, and an optional hint (usually the current y) to keep the user's
vertical order. It returns the top-left corner of every node.

Steps: components are laid out separately and stacked; cycles are broken by reversing back edges; layers come from
the longest path, then nodes move right next to their consumers; long edges get dummy nodes; crossings are reduced
by port-aware barycenter sweeps keeping the best order; vertical positions minimize the squared distance between
connected ports under the order and spacing constraints (isotonic regression), sweeping both ways."""

from __future__ import annotations

from collections.abc import Callable, Hashable, Iterable, Mapping
from dataclasses import dataclass
from math import ceil

__all__ = ["LayoutEdge", "LayoutOptions", "sugiyama_layout"]


@dataclass(frozen=True, slots=True)
class LayoutEdge:
    source: Hashable
    target: Hashable
    source_offset: float = 0.0
    target_offset: float = 0.0


@dataclass(frozen=True, slots=True)
class LayoutOptions:
    layer_gap: float = 80.0
    node_gap: float = 30.0
    edge_gap: float = 12.0
    component_gap: float = 60.0
    crossing_sweeps: int = 12
    placement_sweeps: int = 6
    grid: float = 0.0


class _Dummy:
    __slots__ = ("hint",)

    def __init__(self, hint: float) -> None:
        self.hint = hint


@dataclass(slots=True)
class _Segment:
    source: Hashable
    target: Hashable
    source_offset: float
    target_offset: float


def sugiyama_layout(sizes: Mapping[Hashable, tuple[float, float]], edges: Iterable[LayoutEdge],
                    hints: Mapping[Hashable, float] | None = None,
                    options: LayoutOptions | None = None) -> dict[Hashable, tuple[float, float]]:
    """Top-left positions of the nodes in sizes (width, height), the whole layout starting at (0, 0)."""
    options = options or LayoutOptions()
    hints = hints or {}
    edges = [edge for edge in edges if edge.source in sizes and edge.target in sizes and edge.source != edge.target]
    positions: dict[Hashable, tuple[float, float]] = {}
    top = 0.0

    for component in _components(sizes, edges, hints):
        members = set(component)
        placed = _layout_component(component, [edge for edge in edges if edge.source in members], sizes, hints,
                                   options)
        height = max(y + sizes[node][1] for node, (x, y) in placed.items())

        for node, (x, y) in placed.items():
            positions[node] = (x, y + top)

        top = _snap_up(top + height + options.component_gap, options.grid)

    return positions


def _components(sizes: Mapping[Hashable, tuple[float, float]], edges: list[LayoutEdge],
                hints: Mapping[Hashable, float]) -> list[list[Hashable]]:
    parent = {node: node for node in sizes}

    def root(node: Hashable) -> Hashable:
        while parent[node] != node:
            parent[node] = parent[parent[node]]
            node = parent[node]

        return node

    for edge in edges:
        parent[root(edge.source)] = root(edge.target)

    groups: dict[Hashable, list[Hashable]] = {}

    for node in sizes:
        groups.setdefault(root(node), []).append(node)

    return sorted(groups.values(), key=lambda group: min(hints.get(node, 0.0) for node in group))


def _layout_component(nodes: list[Hashable], edges: list[LayoutEdge], sizes: Mapping[Hashable, tuple[float, float]],
                      hints: Mapping[Hashable, float], options: LayoutOptions) -> dict[Hashable, tuple[float, float]]:
    nodes = sorted(nodes, key=lambda node: hints.get(node, 0.0))
    edges = _acyclic(nodes, edges)
    layer = _layers(nodes, edges)

    segments: list[_Segment] = []
    members: dict[Hashable, int] = dict(layer)

    for edge in edges:
        span = layer[edge.target] - layer[edge.source]

        if span == 1:
            segments.append(_Segment(edge.source, edge.target, edge.source_offset, edge.target_offset))
            continue

        hint = (hints.get(edge.source, 0.0) + hints.get(edge.target, 0.0)) / 2
        previous, offset = edge.source, edge.source_offset

        for step in range(1, span):
            dummy = _Dummy(hint)
            members[dummy] = layer[edge.source] + step
            segments.append(_Segment(previous, dummy, offset, 0.0))
            previous, offset = dummy, 0.0

        segments.append(_Segment(previous, edge.target, offset, edge.target_offset))

    def hint_of(node: Hashable) -> float:
        return node.hint if isinstance(node, _Dummy) else hints.get(node, 0.0)

    layers: list[list[Hashable]] = [[] for _ in range(max(members.values()) + 1)]

    for node in sorted(members, key=hint_of):
        layers[members[node]].append(node)

    def height(node: Hashable) -> float:
        return 0.0 if isinstance(node, _Dummy) else sizes[node][1]

    incoming: dict[Hashable, list[_Segment]] = {node: [] for node in members}
    outgoing: dict[Hashable, list[_Segment]] = {node: [] for node in members}

    for segment in segments:
        outgoing[segment.source].append(segment)
        incoming[segment.target].append(segment)

    tallest = max((sizes[node][1] for node in nodes), default=1.0) or 1.0
    layers = _minimize_crossings(layers, incoming, outgoing, tallest, options.crossing_sweeps)
    tops = _place(layers, incoming, outgoing, height, options)

    lefts: list[float] = []
    left = 0.0

    for nodes_in_layer in layers:
        lefts.append(_snap_up(left, options.grid))
        width = max((sizes[node][0] for node in nodes_in_layer if not isinstance(node, _Dummy)), default=0.0)
        left = lefts[-1] + width + options.layer_gap

    lowest = min(tops[node] for node in nodes)
    lowest = lowest - (lowest % options.grid if options.grid else 0.0)

    return {node: (lefts[layer[node]], tops[node] - lowest) for node in nodes}


def _acyclic(nodes: list[Hashable], edges: list[LayoutEdge]) -> list[LayoutEdge]:
    successors: dict[Hashable, list[LayoutEdge]] = {node: [] for node in nodes}

    for edge in edges:
        successors[edge.source].append(edge)

    state: dict[Hashable, int] = {}
    reversed_edges: set[int] = set()

    for start in nodes:
        if start in state:
            continue

        state[start] = 1
        stack = [(start, iter(successors[start]))]

        while stack:
            node, pending = stack[-1]
            edge = next(pending, None)

            if edge is None:
                state[node] = 2
                stack.pop()
            elif state.get(edge.target) == 1:
                reversed_edges.add(id(edge))
            elif edge.target not in state:
                state[edge.target] = 1
                stack.append((edge.target, iter(successors[edge.target])))

    return [LayoutEdge(edge.target, edge.source, edge.target_offset, edge.source_offset)
            if id(edge) in reversed_edges else edge for edge in edges]


def _layers(nodes: list[Hashable], edges: list[LayoutEdge]) -> dict[Hashable, int]:
    predecessors: dict[Hashable, list[Hashable]] = {node: [] for node in nodes}
    successors: dict[Hashable, list[Hashable]] = {node: [] for node in nodes}

    for edge in edges:
        predecessors[edge.target].append(edge.source)
        successors[edge.source].append(edge.target)

    remaining = {node: len(predecessors[node]) for node in nodes}
    order = [node for node in nodes if not remaining[node]]

    for node in order:
        for successor in successors[node]:
            remaining[successor] -= 1

            if not remaining[successor]:
                order.append(successor)

    layer: dict[Hashable, int] = {}

    for node in order:
        layer[node] = max((layer[predecessor] + 1 for predecessor in predecessors[node]), default=0)

    for node in reversed(order):
        if successors[node]:
            layer[node] = min(layer[successor] for successor in successors[node]) - 1

    return layer


def _minimize_crossings(layers: list[list[Hashable]], incoming: Mapping[Hashable, list[_Segment]],
                        outgoing: Mapping[Hashable, list[_Segment]], tallest: float,
                        sweeps: int) -> list[list[Hashable]]:
    def key(index: int, offset: float) -> float:
        return index + 0.5 * offset / (tallest + 1.0)

    def crossings(order: list[list[Hashable]]) -> int:
        total = 0

        for left, right in zip(order, order[1:]):
            position = {node: index for index, node in enumerate(right)}
            source_position = {node: index for index, node in enumerate(left)}
            ends = sorted((key(source_position[segment.source], segment.source_offset),
                           key(position[segment.target], segment.target_offset))
                          for node in left for segment in outgoing[node])

            total += _inversions([target for _, target in ends])

        return total

    best = [list(layer) for layer in layers]
    best_crossings = crossings(best)
    current = [list(layer) for layer in layers]

    for sweep in range(sweeps):
        downward = sweep % 2 == 0
        indices = range(1, len(current)) if downward else range(len(current) - 2, -1, -1)

        for index in indices:
            reference = current[index - 1] if downward else current[index + 1]
            position = {node: order for order, node in enumerate(reference)}

            def barycenter(node: Hashable, fallback: float) -> float:
                if downward:
                    values = [key(position[segment.source], segment.source_offset) for segment in incoming[node]]
                else:
                    values = [key(position[segment.target], segment.target_offset) for segment in outgoing[node]]

                return sum(values) / len(values) if values else fallback

            layer = current[index]
            scale = len(reference) / max(len(layer), 1)
            current[index] = [node for _, _, node in sorted((barycenter(node, order * scale), order, node) for order, node in enumerate(layer))]

        count = crossings(current)

        if count < best_crossings:
            best, best_crossings = [list(layer) for layer in current], count

        if not best_crossings:
            break

    return best


def _place(layers: list[list[Hashable]], incoming: Mapping[Hashable, list[_Segment]],
           outgoing: Mapping[Hashable, list[_Segment]], height: Callable[[Hashable], float],
           options: LayoutOptions) -> dict[Hashable, float]:
    def gap(first: Hashable, second: Hashable) -> float:
        dummy = isinstance(first, _Dummy) or isinstance(second, _Dummy)
        return height(first) + (options.edge_gap if dummy else options.node_gap)

    tops: dict[Hashable, float] = {}

    for layer in layers:
        top = 0.0

        for index, node in enumerate(layer):
            if index:
                top += gap(layer[index - 1], node)

            tops[node] = top

    def desired(node: Hashable, use_incoming: bool, use_outgoing: bool) -> float | None:
        values = []

        if use_incoming:
            values += [tops[segment.source] + segment.source_offset - segment.target_offset
                       for segment in incoming[node]]

        if use_outgoing:
            values += [tops[segment.target] + segment.target_offset - segment.source_offset
                       for segment in outgoing[node]]

        return sum(values) / len(values) if values else None

    def settle(layer: list[Hashable], use_incoming: bool, use_outgoing: bool) -> None:
        offsets = [0.0]

        for first, second in zip(layer, layer[1:]):
            offsets.append(offsets[-1] + gap(first, second))

        targets, weights = [], []

        for node, offset in zip(layer, offsets):
            wanted = desired(node, use_incoming, use_outgoing)
            targets.append((tops[node] if wanted is None else wanted) - offset)
            weights.append((0.2 if wanted is None else 1.0) * (0.5 if isinstance(node, _Dummy) else 1.0))

        for node, offset, value in zip(layer, offsets, _isotonic(targets, weights)):
            tops[node] = value + offset

    for sweep in range(options.placement_sweeps):
        if sweep % 2 == 0:
            for layer in layers[1:]:
                settle(layer, True, False)
        else:
            for layer in reversed(layers[:-1]):
                settle(layer, False, True)

    for layer in layers:
        settle(layer, True, True)

    if options.grid:
        grid = options.grid

        for layer in layers:
            previous: Hashable | None = None

            for node in layer:
                top = round(tops[node] / grid) * grid

                if previous is not None:
                    top = max(top, _snap_up(tops[previous] + gap(previous, node), grid))

                tops[node] = top
                previous = node

    return tops


def _inversions(values: list[float]) -> int:
    """Pairs i < j with values[i] > values[j], in O(n log n) with a Fenwick tree over the value ranks."""
    ranks = {value: rank for rank, value in enumerate(sorted(set(values)), 1)}
    tree = [0] * (len(ranks) + 1)
    total = 0

    for seen, value in enumerate(values):
        rank = ranks[value]
        index, not_greater = rank, 0

        while index:
            not_greater += tree[index]
            index -= index & -index

        total += seen - not_greater

        while rank < len(tree):
            tree[rank] += 1
            rank += rank & -rank

    return total


def _isotonic(values: list[float], weights: list[float]) -> list[float]:
    """Nondecreasing sequence closest to values in weighted least squares (pool adjacent violators)."""
    blocks: list[list[float]] = []

    for value, weight in zip(values, weights):
        blocks.append([value, weight, 1])

        while len(blocks) > 1 and blocks[-2][0] > blocks[-1][0]:
            value_b, weight_b, count_b = blocks.pop()
            value_a, weight_a, count_a = blocks[-1]
            total = weight_a + weight_b
            blocks[-1] = [(value_a * weight_a + value_b * weight_b) / total, total, count_a + count_b]

    result: list[float] = []

    for value, _, count in blocks:
        result.extend([value] * count)

    return result


def _snap_up(value: float, grid: float) -> float:
    return ceil(value / grid - 1e-9) * grid if grid else value
