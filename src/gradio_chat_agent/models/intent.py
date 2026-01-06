from datetime import datetime
from typing import Any, Literal

from pydantic import ConfigDict, Field, model_validator

from ..execution.modes import ExecutionMode
from .base import ActionId, ModelBase, RequestId


IntentType = Literal["action_call", "clarification_request"]


class ChatIntent(ModelBase):
    """
    Structured intent produced by the chat agent.

    It may either:
    - request an action execution, or
    - ask the user for clarification.
    """

    model_config = ConfigDict(extra="forbid")

    type: IntentType = Field(
        ...,
        description="Type of intent being expressed.",
    )

    request_id: RequestId = Field(
        ...,
        description="Unique identifier for this intent.",
    )

    timestamp: datetime = Field(
        ...,
        description="Timestamp when the intent was created.",
    )

    execution_mode: ExecutionMode | None = Field(
        default=None,
        description="Execution mode in which this intent was generated.",
    )

    # Action call fields
    action_id: ActionId | None = Field(
        default=None,
        description="Identifier of the action being requested (for action_call).",
    )

    inputs: dict[str, Any] | None = Field(
        default=None,
        description="Inputs for the requested action.",
    )

    confirmed: bool = Field(
        default=False,
        description="Whether the user has explicitly confirmed execution.",
    )

    # Clarification fields
    question: str | None = Field(
        default=None,
        description="Clarifying question posed to the user.",
    )

    choices: list[str] = Field(
        default_factory=list,
        description="Optional list of choices presented to the user.",
    )

    trace: dict[str, Any] = Field(
        default_factory=dict,
        description="Optional diagnostic metadata for debugging or analysis.",
    )

    @model_validator(mode="after")
    def validate_by_type(self) -> "ChatIntent":
        if self.type == "action_call":
            if not self.action_id or self.inputs is None:
                raise ValueError("action_call requires action_id and inputs")
            if self.question is not None:
                raise ValueError(
                    "action_call intents must not include a question"
                )
        if self.type == "clarification_request":
            if not self.question:
                raise ValueError("clarification_request requires question")
            if self.action_id is not None or self.inputs is not None:
                raise ValueError(
                    "clarification_request must not include action_id or inputs"
                )
        return self

    @model_validator(mode="after")
    def validate_mode_consistency(self) -> "ChatIntent":
        # Example: forbid setting confirmed=True in interactive mode without explanation
        if self.execution_mode == "interactive" and self.confirmed:
            # Not strictly necessary, but we enforce that interactive confirmations
            # must be explicitly traced.
            source = self.trace.get("confirmation_source")
            if not source:
                raise ValueError(
                    "Interactive mode intents with confirmed=True must set trace.confirmation_source"
                )
        return self
