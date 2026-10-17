import itertools
import random

from bolt.core.layout import LayoutEdge, LayoutOptions, sugiyama_layout


def boxes_overlap(first, second):
    (x1, y1, w1, h1), (x2, y2, w2, h2) = first, second
    return x1 < x2 + w2 and x2 < x1 + w1 and y1 < y2 + h2 and y2 < y1 + h1


def check_layout(sizes, edges, positions):
    assert set(positions) == set(sizes)
    for first, second in itertools.combinations(sizes, 2):
        assert not boxes_overlap((*positions[first], *sizes[first]), (*positions[second], *sizes[second])), \
            (first, second)


def test_empty_and_single():
    assert sugiyama_layout({}, []) == {}
    assert sugiyama_layout({"a": (10, 10)}, []) == {"a": (0.0, 0.0)}


def test_chain_flows_right_with_aligned_ports():
    sizes = {name: (180, 70) for name in "abc"}
    edges = [LayoutEdge("a", "b", 40, 60), LayoutEdge("b", "c", 40, 40)]
    positions = sugiyama_layout(sizes, edges, options=LayoutOptions(layer_gap=80))
    assert [positions[name][0] for name in "abc"] == [0, 260, 520]
    assert positions["a"][1] + 40 == positions["b"][1] + 60
    assert positions["b"][1] + 40 == positions["c"][1] + 40


def test_sources_sit_next_to_their_consumer():
    sizes = {name: (100, 50) for name in ("start", "middle", "late_input", "end")}
    edges = [LayoutEdge("start", "middle"), LayoutEdge("middle", "end"), LayoutEdge("late_input", "end")]
    positions = sugiyama_layout(sizes, edges)
    assert positions["late_input"][0] == positions["middle"][0]


def test_crossings_are_removed():
    sizes = {name: (100, 50) for name in ("a", "b", "x", "y")}
    edges = [LayoutEdge("a", "y"), LayoutEdge("b", "x")]
    positions = sugiyama_layout(sizes, edges, hints={"a": 0, "b": 100, "x": 0, "y": 100})
    assert (positions["a"][1] < positions["b"][1]) == (positions["y"][1] < positions["x"][1])


def test_cycles_components_and_grid():
    sizes = {name: (180, 70 + 20 * (index % 3)) for index, name in enumerate("abcdefgh")}
    edges = [LayoutEdge("a", "b", 40, 40), LayoutEdge("b", "c", 40, 60), LayoutEdge("c", "a", 60, 40),
             LayoutEdge("d", "e", 40, 40), LayoutEdge("e", "f", 40, 40), LayoutEdge("d", "f", 40, 60)]
    positions = sugiyama_layout(sizes, edges, options=LayoutOptions(grid=20))
    check_layout(sizes, edges, positions)
    assert all(x % 20 == 0 and y % 20 == 0 for x, y in positions.values())
    first = max(positions[name][1] + sizes[name][1] for name in "abc")
    assert min(positions[name][1] for name in "def") >= first
    assert min(x for x, _ in positions.values()) == 0 and min(y for _, y in positions.values()) == 0


def test_random_graphs_never_overlap_and_edges_go_right():
    for seed in range(20):
        generator = random.Random(seed)
        count = generator.randint(2, 40)
        sizes = {index: (180, generator.choice((70, 90, 110))) for index in range(count)}
        edges = [LayoutEdge(generator.randrange(index), index, 40, 40 + 20 * generator.randrange(3))
                 for index in range(1, count) for _ in range(generator.randint(0, 2))]
        positions = sugiyama_layout(sizes, edges, {index: generator.random() for index in sizes},
                                    LayoutOptions(grid=20))
        check_layout(sizes, edges, positions)
        for edge in edges:
            assert positions[edge.target][0] >= positions[edge.source][0] + 180
