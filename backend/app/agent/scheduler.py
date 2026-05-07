import uuid

from app.agent.dag_validator import CircularDependencyError
from app.models.task import Task


def topological_sort(tasks: list[Task]) -> list[list[Task]]:
    """Group tasks into execution waves respecting dependencies.

    Returns a list of waves; tasks within a wave have no mutual dependencies
    and can execute concurrently. Raises CircularDependencyError if a cycle
    is detected at runtime (real UUIDs, so full detection is possible).
    """
    id_to_task: dict[uuid.UUID, Task] = {t.id: t for t in tasks}
    in_degree: dict[uuid.UUID, int] = {t.id: 0 for t in tasks}
    adj: dict[uuid.UUID, list[uuid.UUID]] = {t.id: [] for t in tasks}

    for task in tasks:
        for dep_id in (task.dependencies or []):
            if dep_id in id_to_task:
                adj[dep_id].append(task.id)
                in_degree[task.id] += 1

    waves: list[list[Task]] = []
    ready = [tid for tid, deg in in_degree.items() if deg == 0]

    while ready:
        wave = [id_to_task[tid] for tid in ready]
        waves.append(wave)
        next_ready: list[uuid.UUID] = []
        for tid in ready:
            for neighbor in adj[tid]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    next_ready.append(neighbor)
        ready = next_ready

    total_scheduled = sum(len(w) for w in waves)
    if total_scheduled != len(tasks):
        raise CircularDependencyError(list(range(len(tasks))))

    return waves
