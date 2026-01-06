import json
from typing import Any

from ..persistence.memory_repo import MemoryRepository
from ..persistence.repo import Identity, StateRepository


def export_session_json(
    repo: StateRepository, mem: MemoryRepository, ident: Identity
) -> str:
    snap = repo.load_latest_snapshot(ident)
    execs = repo.list_recent_executions(ident, limit=5000)
    facts = mem.get_facts(ident=ident)

    payload: dict[str, Any] = {
        "identity": {"session_id": ident.session_id, "user_id": ident.user_id},
        "facts": facts,
        "latest_snapshot": snap.model_dump() if snap else None,
        "executions": [e.model_dump() for e in execs],
    }
    return json.dumps(payload, indent=2, ensure_ascii=False)
