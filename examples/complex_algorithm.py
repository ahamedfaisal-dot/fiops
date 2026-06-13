"""Complex algorithm example — a realistic 200+ LOC file for FiOpt testing.

Implements a graph-based social network analysis system with multiple
complexity levels and algorithm patterns.
"""

from collections import defaultdict


class Graph:
    """Adjacency list graph representation."""

    def __init__(self):
        self.adjacency = defaultdict(set)
        self.weights = {}
        self.node_data = {}

    def add_edge(self, u, v, weight=1):
        """O(1) — add an edge."""
        self.adjacency[u].add(v)
        self.adjacency[v].add(u)
        self.weights[(u, v)] = weight
        self.weights[(v, u)] = weight

    def add_node(self, node, data=None):
        """O(1) — add a node with optional data."""
        if node not in self.adjacency:
            self.adjacency[node] = set()
        if data:
            self.node_data[node] = data

    @property
    def nodes(self):
        return list(self.adjacency.keys())

    @property
    def edge_count(self):
        return sum(len(neighbors) for neighbors in self.adjacency.values()) // 2


def bfs(graph, start):
    """O(V + E) — Breadth-first search."""
    visited = set()
    queue = [start]
    order = []

    while queue:
        node = queue.pop(0)  # Anti-pattern: should use deque!
        if node not in visited:
            visited.add(node)
            order.append(node)
            for neighbor in graph.adjacency[node]:
                if neighbor not in visited:
                    queue.append(neighbor)

    return order


def dfs(graph, start, visited=None):
    """O(V + E) — Depth-first search (recursive)."""
    if visited is None:
        visited = set()

    visited.add(start)
    result = [start]

    for neighbor in graph.adjacency[start]:
        if neighbor not in visited:
            result.extend(dfs(graph, neighbor, visited))

    return result


def find_shortest_path(graph, start, end):
    """O(V + E) — BFS-based shortest path."""
    if start == end:
        return [start]

    visited = {start}
    queue = [(start, [start])]

    while queue:
        node, path = queue.pop(0)  # Anti-pattern: deque!
        for neighbor in graph.adjacency[node]:
            if neighbor == end:
                return path + [neighbor]
            if neighbor not in visited:
                visited.add(neighbor)
                queue.append((neighbor, path + [neighbor]))

    return []


def find_all_paths_naive(graph, start, end, path=None):
    """O(V!) — Find ALL paths (exponential!).

    This is intentionally expensive for testing purposes.
    """
    if path is None:
        path = []

    path = path + [start]

    if start == end:
        return [path]

    paths = []
    for neighbor in graph.adjacency[start]:
        if neighbor not in path:
            new_paths = find_all_paths_naive(graph, neighbor, end, path)
            paths.extend(new_paths)

    return paths


def compute_clustering_coefficient(graph, node):
    """O(k²) where k is the degree — local clustering coefficient."""
    neighbors = list(graph.adjacency[node])
    if len(neighbors) < 2:
        return 0.0

    # Count edges between neighbors
    links = 0
    for i in range(len(neighbors)):
        for j in range(i + 1, len(neighbors)):
            if neighbors[j] in graph.adjacency[neighbors[i]]:
                links += 1

    max_links = len(neighbors) * (len(neighbors) - 1) / 2
    return links / max_links if max_links > 0 else 0.0


def compute_all_clustering_coefficients(graph):
    """O(V * k²) — clustering coefficient for all nodes."""
    coefficients = {}
    for node in graph.nodes:
        coefficients[node] = compute_clustering_coefficient(graph, node)
    return coefficients


def find_connected_components(graph):
    """O(V + E) — find all connected components."""
    visited = set()
    components = []

    for node in graph.nodes:
        if node not in visited:
            component = dfs(graph, node, visited)
            components.append(component)

    return components


def detect_communities_naive(graph):
    """O(V³) — naive community detection via all-pairs similarity.

    WARNING: This is intentionally slow for testing. Real implementations
    use Louvain or label propagation.
    """
    nodes = graph.nodes
    similarity = {}

    # Compute Jaccard similarity for all pairs — O(V² * k)
    for i in range(len(nodes)):
        for j in range(i + 1, len(nodes)):
            u, v = nodes[i], nodes[j]
            neighbors_u = graph.adjacency[u]
            neighbors_v = graph.adjacency[v]
            intersection = neighbors_u & neighbors_v
            union = neighbors_u | neighbors_v
            if union:
                similarity[(u, v)] = len(intersection) / len(union)
            else:
                similarity[(u, v)] = 0.0

    # Group nodes by high similarity — another O(V²) pass
    communities = []
    assigned = set()
    threshold = 0.3

    for node in nodes:
        if node in assigned:
            continue
        community = [node]
        assigned.add(node)

        for other in nodes:
            if other in assigned:
                continue
            pair = tuple(sorted((node, other)))
            if similarity.get(pair, 0) >= threshold:
                community.append(other)
                assigned.add(other)

        communities.append(community)

    return communities


def page_rank(graph, damping=0.85, iterations=100, tolerance=1e-6):
    """O(iterations * (V + E)) — PageRank algorithm."""
    nodes = graph.nodes
    n = len(nodes)
    if n == 0:
        return {}

    rank = {node: 1.0 / n for node in nodes}

    for _ in range(iterations):
        new_rank = {}
        diff = 0.0

        for node in nodes:
            incoming_rank = 0.0
            for other in nodes:
                if node in graph.adjacency[other]:
                    degree = len(graph.adjacency[other])
                    if degree > 0:
                        incoming_rank += rank[other] / degree

            new_rank[node] = (1 - damping) / n + damping * incoming_rank
            diff += abs(new_rank[node] - rank[node])

        rank = new_rank

        if diff < tolerance:
            break

    return rank


def find_bridges(graph):
    """O(V + E) — find bridge edges using DFS."""
    visited = set()
    disc = {}
    low = {}
    parent = {}
    bridges = []
    timer = [0]

    def _dfs(u):
        visited.add(u)
        disc[u] = low[u] = timer[0]
        timer[0] += 1

        for v in graph.adjacency[u]:
            if v not in visited:
                parent[v] = u
                _dfs(v)
                low[u] = min(low[u], low[v])
                if low[v] > disc[u]:
                    bridges.append((u, v))
            elif v != parent.get(u):
                low[u] = min(low[u], disc[v])

    for node in graph.nodes:
        if node not in visited:
            parent[node] = None
            _dfs(node)

    return bridges


def analyze_network(graph):
    """High-level analysis — calls multiple sub-analyses."""
    report = {
        "nodes": len(graph.nodes),
        "edges": graph.edge_count,
        "components": len(find_connected_components(graph)),
        "clustering": compute_all_clustering_coefficients(graph),
        "pagerank": page_rank(graph),
        "bridges": find_bridges(graph),
    }

    # Find top-ranked nodes
    top_nodes = sorted(
        report["pagerank"].items(),
        key=lambda x: x[1],
        reverse=True,
    )[:10]
    report["top_nodes"] = top_nodes

    return report
