from __future__ import annotations

from ..persistence.memory_repo import MemoryRepository
from ..persistence.repo import ProjectIdentity, StateRepository


def build_memory_block(
    repo: StateRepository,
    mem: MemoryRepository,
    ident: ProjectIdentity,
    limit: int = 12,
) -> str:
    recent = repo.list_recent_executions(ident, limit=limit)
    facts = mem.get_facts(ident=ident)

    lines: list[str] = []
    lines.append("Session facts (explicit memory):")
    if facts:
        for k in sorted(facts.keys()):
            lines.append(f"- {k} = {facts[k]!r}")
    else:
        lines.append("- (none)")

    lines.append("")
    lines.append("Recent outcomes:")
    if not recent:
        lines.append("- (none)")
    else:
        for r in recent[-limit:]:
            if r.error:
                lines.append(f"- {r.action_id} => {r.status} ({r.error.code})")
            else:
                lines.append(f"- {r.action_id} => {r.status}")

    return "\n".join(lines)
