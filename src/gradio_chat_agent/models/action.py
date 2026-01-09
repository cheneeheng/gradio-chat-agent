"""Data models for defining executable actions.

This module defines the schema for registering actions, including their
permissions, preconditions, and input requirements.
"""

from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field

from gradio_chat_agent.models.enums import ActionRisk, ActionVisibility


class ActionPermission(BaseModel):
    """Defines the security and governance rules for an action.

    Attributes:
        confirmation_required: If True, the user must explicitly confirm execution.
        risk: The risk level (LOW, MEDIUM, HIGH) impacting approval flows.
        visibility: Whether the action is shown to standard users.
    """

    confirmation_required: bool = Field(
        ..., description="If True, the user must explicitly confirm execution."
    )
    risk: ActionRisk = Field(
        ...,
        description="The risk level (LOW, MEDIUM, HIGH) impacting approval flows.",
    )
    visibility: ActionVisibility = Field(
        ..., description="Whether the action is shown to standard users."
    )


class ActionPrecondition(BaseModel):
    """A condition that must be met before an action can execute.

    Attributes:
        id: Stable identifier for the precondition.
        description: Human-readable explanation of the requirement.
        expr: Python expression string evaluated against the state.
    """

    id: str = Field(
        ...,
        pattern=r"^[a-z0-9]+(\.[a-z0-9]+)*$",
        description="Stable identifier for the precondition.",
    )
    description: str = Field(
        ..., description="Human-readable explanation of the requirement."
    )
    expr: str = Field(
        ...,
        description="Python expression string evaluated against the state.",
    )


class ActionEffects(BaseModel):
    """Declarative description of an action's side effects.

    Attributes:
        may_change: List of state paths that this action might modify.
    """

    may_change: list[str] = Field(
        ..., description="List of state paths that this action might modify."
    )


class ActionDeclaration(BaseModel):
    """Complete definition of a registered action.

    Attributes:
        action_id: Unique, dot-notation identifier (e.g., 'demo.counter.set').
        title: Short human-readable name.
        description: Detailed explanation of behavior.
        targets: List of component IDs this action affects.
        input_schema: JSON Schema defining valid input parameters.
        preconditions: List of checks to run before execution.
        effects: Declaration of expected state changes.
        permission: Security and governance settings.
    """

    model_config = ConfigDict(use_enum_values=True)

    action_id: str = Field(
        ...,
        pattern=r"^[a-z0-9]+(\.[a-z0-9]+)*$",
        description="Unique, dot-notation identifier (e.g., 'demo.counter.set').",
    )
    title: str = Field(..., description="Short human-readable name.")
    description: str = Field(
        ..., description="Detailed explanation of behavior."
    )
    targets: list[str] = Field(
        ...,
        min_length=1,
        description="List of component IDs this action affects.",
    )
    input_schema: dict[str, Any] = Field(
        ..., description="JSON Schema defining valid input parameters."
    )
    preconditions: list[ActionPrecondition] = Field(
        default_factory=list,
        description="List of checks to run before execution.",
    )
    effects: Optional[ActionEffects] = Field(
        default=None, description="Declaration of expected state changes."
    )
    permission: ActionPermission = Field(
        ..., description="Security and governance settings."
    )
