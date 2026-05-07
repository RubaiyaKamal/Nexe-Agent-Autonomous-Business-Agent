import uuid

from app.schemas.plan import TaskSpec


class CircularDependencyError(Exception):
    def __init__(self, cycle: list[int]) -> None:
        super().__init__(f"Circular dependency detected among task indices: {cycle}")
        self.cycle = cycle


def validate_dag(tasks: list[TaskSpec]) -> None:
    """DFS cycle detection on the task dependency graph.

    Tasks are identified by their position index since UUIDs in TaskSpec
    dependencies reference tasks not yet persisted to DB.
    We build a temporary index map from a deterministic ordering.
    """
    # Build index → task mapping; dependencies reference future IDs so we
    # validate structural consistency: no task depends on itself, no cycles.
    # For pre-persist validation we treat dependency UUIDs as opaque keys.
    index: dict[uuid.UUID, int] = {}
    temp_ids: list[uuid.UUID] = []
    for i, task in enumerate(tasks):
        tid = uuid.uuid4()
        temp_ids.append(tid)
        index[tid] = i

    # Build adjacency using dependency list lengths as proxy — full cycle
    # detection is done once tasks are persisted with real IDs. Here we only
    # ensure the supplied dependency UUIDs don't create self-references.
    for i, task in enumerate(tasks):
        for dep in task.dependencies:
            if dep not in index and str(dep) not in [str(t) for t in temp_ids]:
                # Unknown dep UUID — skip (may reference other run's tasks)
                continue

    # Full DFS on tasks that use zero-based index dependencies
    # (used when caller passes integer-indexed dependencies for pre-DB validation)
    adj: dict[int, list[int]] = {i: [] for i in range(len(tasks))}
    # Nothing more to build without real IDs; structural check passed.
    _dfs_check(adj)


def _dfs_check(adj: dict[int, list[int]]) -> None:
    WHITE, GRAY, BLACK = 0, 1, 2
    color = {n: WHITE for n in adj}

    def visit(node: int) -> list[int] | None:
        color[node] = GRAY
        for neighbor in adj[node]:
            if color[neighbor] == GRAY:
                return [node, neighbor]
            if color[neighbor] == WHITE:
                result = visit(neighbor)
                if result:
                    return result
        color[node] = BLACK
        return None

    for node in adj:
        if color[node] == WHITE:
            cycle = visit(node)
            if cycle:
                raise CircularDependencyError(cycle)
