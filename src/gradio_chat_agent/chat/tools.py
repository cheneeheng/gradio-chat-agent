from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from ..execution.modes import ExecutionMode


class ProposeActionCall(BaseModel):
    """
    Propose a single action call from the UI action registry.

    Use this when the user request can be satisfied by exactly one action call.
    """

    model_config = ConfigDict(extra="forbid")

    action_id: str = Field(
        ...,
        description="Action identifier from the action registry (must be exact).",
    )

    inputs: dict[str, Any] = Field(
        default_factory=dict,
        description="Action inputs; must validate against the action's input_schema.",
    )

    confirmed: bool = Field(
        False,
        description="Set true only if the user explicitly confirmed a gated/high-risk action.",
    )

    execution_mode: ExecutionMode | None = Field(
        None,
        description="Execution mode under which this proposal was made.",
    )


class ProposeExecutionPlan(BaseModel):
    """
    Propose a multi-step plan consisting of ordered action calls.

    Use this only when the user request clearly implies multiple dependent steps
    that can be executed deterministically.
    """

    model_config = ConfigDict(extra="forbid")

    plan_id: str = Field(
        ...,
        description="Stable identifier for this plan instance (unique per request).",
    )

    steps: list[ProposeActionCall] = Field(
        ...,
        description="Ordered list of action calls to execute.",
        min_length=1,
    )
