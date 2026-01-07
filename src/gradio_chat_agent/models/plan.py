"""Data models for multi-step execution plans.

This module defines the structure for plans proposed by the agent when multiple
dependent actions are required to fulfill a user request.
"""

from pydantic import BaseModel, Field

from gradio_chat_agent.models.intent import ChatIntent


class ExecutionPlan(BaseModel):
    """Represents a sequence of intended actions.

    Attributes:
        plan_id: Unique identifier for this plan instance.
        steps: Ordered list of ChatIntent objects to be executed.
    """

    plan_id: str = Field(
        ...,
        description="Unique identifier for this plan instance."
    )
    steps: list[ChatIntent] = Field(
        ...,
        min_length=1,
        description="Ordered list of ChatIntent objects to be executed."
    )
