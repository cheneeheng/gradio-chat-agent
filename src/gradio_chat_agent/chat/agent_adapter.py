from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from ..execution.modes import ExecutionMode
from ..models.intent import ChatIntent


class AgentAdapter:
    """
    Placeholder adapter.

    Replace `message_to_intent` with your floating-chatbot / LLM integration.
    The engine expects a ChatIntent; everything else is your choice.
    """

    def __init__(self, *, default_mode: ExecutionMode = "interactive") -> None:
        self.default_mode = default_mode

    def message_to_intent(
        self,
        *,
        message: str,
        state_context: dict[str, Any],
        forced_action_id: str | None = None,
        forced_inputs: dict[str, Any] | None = None,
        confirmed: bool = False,
    ) -> ChatIntent:
        # Minimal “command” mode for dev:
        # If forced_action_id is provided, we build an action_call intent.
        if forced_action_id:
            return ChatIntent(
                type="action_call",
                request_id=str(uuid4()),
                timestamp=datetime.now(timezone.utc),
                action_id=forced_action_id,
                inputs=forced_inputs or {},
                confirmed=confirmed,
                trace={"source": "forced_action"},
            )

        # Otherwise, we request clarification (since we’re not actually parsing NL here).
        return ChatIntent(
            type="clarification_request",
            request_id=str(uuid4()),
            timestamp=datetime.now(timezone.utc),
            question="I need an explicit action_id and inputs (agent adapter not yet implemented).",
            choices=[],
            trace={"source": "stub"},
        )
