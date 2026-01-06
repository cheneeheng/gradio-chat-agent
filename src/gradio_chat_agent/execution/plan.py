from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from ..models.intent import ChatIntent


class ExecutionPlan(BaseModel):
    """
    Multi-step execution plan consisting of ordered action_call intents.
    """

    model_config = ConfigDict(extra="forbid")

    plan_id: str = Field(
        ...,
        description="Identifier for this multi-step execution plan.",
    )

    steps: list[ChatIntent] = Field(
        ...,
        description="Ordered list of action_call intents to execute.",
        min_length=1,
    )
