from typing import Iterable

from ..models.execution_result import StateDiffEntry


def format_state_diff_markdown(diff: Iterable[StateDiffEntry]) -> str:
    diff = list(diff)
    if not diff:
        return "No state changes."

    lines: list[str] = ["### State diff"]
    for d in diff:
        if d.op in ("add", "replace"):
            lines.append(f"- **{d.op}** `{d.path}` = `{d.value}`")
        else:
            lines.append(f"- **{d.op}** `{d.path}`")
    return "\n".join(lines)
