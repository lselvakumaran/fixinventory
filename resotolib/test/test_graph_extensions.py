from typing import Dict, List

from networkx import DiGraph
from pytest import fixture

from resotolib.graph.graph_extensions import dependent_node_iterator


@fixture
def graph() -> DiGraph:
    g = DiGraph()
    for i in range(1, 14):
        g.add_node(i, id=i)
    g.add_edges_from([(1, 2), (1, 3), (2, 3)])  # island 1
    g.add_edges_from([(4, 5), (4, 6), (6, 7)])  # island 2
    g.add_edges_from(
        [(8, 9), (9, 10), (9, 11), (8, 12), (12, 11), (12, 13)]
    )  # island 3
    return g


def test_reversed_directed_traversal(graph: DiGraph):
    result = [list(island) for island in dependent_node_iterator(graph)]
    assert len(result) == 3  # 3 steps to complete

    def nodes(*ls: int) -> List[Dict[str, int]]:
        return [{"id": e} for e in ls]

    assert result == [
        nodes(3, 5, 7, 10, 11, 13),
        nodes(2, 6, 9, 12),
        nodes(1, 4, 8),
    ]


def test_delete_nodes(graph: DiGraph):
    to_delete = graph.copy()
    for parallel in dependent_node_iterator(graph):
        for node in parallel:
            to_delete.remove_node(node["id"])
    assert len(to_delete.nodes) == 0
