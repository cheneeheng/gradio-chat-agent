from copy import deepcopy
from typing import Any

from ..models.execution_result import ExecutionResult


def _set_path(
    components: dict[str, dict[str, Any]], dotted_path: str, value: Any
) -> None:
    # dotted_path example: "components.demo.counter.value"
    parts = dotted_path.split(".")
    if not parts or parts[0] != "components":
        raise ValueError(
            f"Unsupported diff path (expected 'components.*'): {dotted_path}"
        )

    cur: Any = components
    for p in parts[1:-1]:
        if p not in cur or not isinstance(cur[p], dict):
            cur[p] = {}
        cur = cur[p]
    cur[parts[-1]] = value


def _remove_path(
    components: dict[str, dict[str, Any]], dotted_path: str
) -> None:
    parts = dotted_path.split(".")
    if not parts or parts[0] != "components":
        raise ValueError(
            f"Unsupported diff path (expected 'components.*'): {dotted_path}"
        )

    cur: Any = components
    for p in parts[1:-1]:
        if p not in cur or not isinstance(cur[p], dict):
            return
        cur = cur[p]
    cur.pop(parts[-1], None)


def replay_components_from_results(
    *,
    initial_components: dict[str, dict[str, Any]],
    results: list[ExecutionResult],
) -> dict[str, dict[str, Any]]:
    components = deepcopy(initial_components)

    for r in results:
        if r.status != "success":
            continue
        for d in r.state_diff:
            match d.op:
                case "add" | "replace":
                    _set_path(components, d.path, d.value)
                case "remove":
                    _remove_path(components, d.path)
                case _:
                    raise ValueError(f"Unknown diff op: {d.op}")

    return components
