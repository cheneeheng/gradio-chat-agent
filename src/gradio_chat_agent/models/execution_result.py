"""Data models for reporting execution outcomes.

This module defines the structures returned by the Execution Engine after an
attempt to execute an intent.
"""

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field, PrivateAttr

from gradio_chat_agent.models.enums import ExecutionStatus, StateDiffOp


class StateDiffEntry(BaseModel):
    """Represents a single atomic change to the application state.

    Attributes:
        path: Dot-separated path to the changed field (e.g., 'component.value').
        op: The operation performed (add, remove, replace).
        value: The new value after the operation (if applicable).
    """

    path: str = Field(
        ...,
        description="Dot-separated path to the changed field (e.g., 'component.value').",
    )
    op: StateDiffOp = Field(
        ..., description="The operation performed (add, remove, replace)."
    )
    value: Optional[Any] = Field(
        None, description="The new value after the operation (if applicable)."
    )


class ExecutionError(BaseModel):
    """Details regarding a failure or rejection.

    Attributes:
        code: Machine-readable error code (e.g., 'policy_violation').
        detail: Human-readable explanation of the error.
    """

    code: str = Field(
        ...,
        description="Machine-readable error code (e.g., 'policy_violation').",
    )
    detail: str = Field(
        ..., description="Human-readable explanation of the error."
    )


class ExecutionResult(BaseModel):
    """The result of an action execution attempt.

    Attributes:
        request_id: The ID of the intent that triggered this execution.
        action_id: The ID of the action attempted.
        status: The final outcome (success, rejected, failed).
        timestamp: When the execution completed.
        message: A summary message suitable for display to the user.
        state_snapshot_id: ID of the resulting state snapshot.
        state_diff: List of changes applied to the state.
        error: Error details if the status is REJECTED or FAILED.
        simulated: Whether this execution was a simulation (dry-run).
        metadata: Arbitrary metadata about the execution (e.g. costs, media hashes).
    """

    model_config = ConfigDict(use_enum_values=True)

    request_id: str = Field(
        ..., description="The ID of the intent that triggered this execution."
    )
    user_id: Optional[str] = Field(
        default=None, description="The ID of the user who triggered this execution."
    )
    action_id: str = Field(
        ...,
        pattern=r"^[a-z0-9]+(\.[a-z0-9]+)*$",
        description="The ID of the action attempted.",
    )
    status: ExecutionStatus = Field(
        ..., description="The final outcome (success, rejected, failed)."
    )
    timestamp: datetime = Field(
        default_factory=datetime.now,
        description="When the execution completed.",
    )
    execution_time_ms: Optional[float] = Field(
        default=None, description="The time taken to execute the action in milliseconds."
    )
    cost: Optional[float] = Field(
        default=None, description="The cost of the execution."
    )
    message: Optional[str] = Field(
        default=None,
        description="A summary message suitable for display to the user.",
    )
    state_snapshot_id: str = Field(
        ..., description="ID of the resulting state snapshot."
    )
    state_diff: list[StateDiffEntry] = Field(
        default_factory=list,
        description="List of changes applied to the state.",
    )
    intent: Optional[dict[str, Any]] = Field(
        default=None,
        description="The full intent object that triggered this execution.",
    )
    error: Optional[ExecutionError] = Field(
        default=None,
        description="Error details if the status is REJECTED or FAILED.",
    )
    simulated: bool = Field(
        default=False,
        description="Whether this execution was a simulation (dry-run).",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Arbitrary metadata about the execution (e.g. costs, media hashes).",
    )
    _simulated_state: Optional[dict[str, Any]] = PrivateAttr(default=None)
