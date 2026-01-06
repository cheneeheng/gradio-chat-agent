from datetime import datetime
from typing import Any

from pydantic import Field, model_validator

from .base import (
    ActionId,
    ExecutionStatus,
    ModelBase,
    RequestId,
)


class StateDiffEntry(ModelBase):
    """
    Single atomic change applied to the state.
    """

    path: str = Field(
        ...,
        description="Path in the state that was modified.",
    )

    op: str = Field(
        ...,
        description="Type of modification applied.",
        pattern="^(add|remove|replace)$",
    )

    value: Any = Field(
        None,
        description="New value applied at the path, if applicable.",
    )


class ExecutionError(ModelBase):
    """
    Error details when execution fails or is rejected.
    """

    code: str = Field(
        ...,
        description="Machine-readable error code.",
    )

    detail: str = Field(
        ...,
        description="Human-readable error explanation.",
    )


class ExecutionResult(ModelBase):
    """
    Result of attempting to execute an action.
    """

    request_id: RequestId = Field(
        ...,
        description="Identifier of the originating intent.",
    )

    action_id: ActionId = Field(
        ...,
        description="Identifier of the action that was attempted.",
    )

    status: ExecutionStatus = Field(
        ...,
        description="Outcome of the execution attempt.",
    )

    timestamp: datetime = Field(
        ...,
        description="Timestamp when execution completed.",
    )

    message: str = Field(
        ...,
        description="Human-readable summary of the outcome.",
    )

    state_snapshot_id: str = Field(
        ...,
        description="Identifier of the resulting state snapshot.",
    )

    state_diff: list[StateDiffEntry] = Field(
        default_factory=list,
        description="List of state changes applied by the action.",
    )

    error: ExecutionError | None = Field(
        None,
        description="Error details when execution fails or is rejected.",
    )

    @model_validator(mode="after")
    def validate_error(self):
        if self.status in ("failed", "rejected") and self.error is None:
            raise ValueError(
                "error must be provided when status is failed or rejected"
            )
        return self
