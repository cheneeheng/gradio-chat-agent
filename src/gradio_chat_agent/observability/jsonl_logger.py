import json
from pathlib import Path
from typing import Any

from ..models.execution_result import ExecutionResult
from ..models.intent import ChatIntent
from ..persistence.repo import Identity


class JsonlAuditLogger:
    def __init__(self, path: str = "./audit_log.jsonl") -> None:
        self.path = Path(path)

    def log_intent_and_result(
        self, *, ident: Identity, intent: ChatIntent, result: ExecutionResult
    ) -> None:
        record: dict[str, Any] = {
            "session_id": ident.session_id,
            "user_id": ident.user_id,
            "intent": intent.model_dump(),
            "result": result.model_dump(),
        }
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
