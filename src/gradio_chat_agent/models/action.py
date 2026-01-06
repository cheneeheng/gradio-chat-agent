from typing import Any

from pydantic import Field

from .base import (
    ActionId,
    ComponentId,
    ModelBase,
    RiskLevel,
    Visibility,
)


class ActionPermission(ModelBase):
    """
    Permission and risk metadata governing action execution.
    """

    confirmation_required: bool = Field(
        ...,
        description="Whether explicit user confirmation is required before execution.",
    )

    risk: RiskLevel = Field(
        ...,
        description="Risk level associated with executing this action.",
    )

    visibility: Visibility = Field(
        ...,
        description="Whether this action is visible to end users or only developers.",
    )

    required_roles: set[str] = Field(
        default_factory=set,
        description="Roles required to execute this action. Empty means any authenticated user.",
    )

    base_cost: int = Field(default=1)


class ActionPrecondition(ModelBase):
    """
    A single precondition that must evaluate to true before execution.
    """

    id: str = Field(
        ...,
        description="Stable identifier for the precondition.",
        pattern=r"^[a-z0-9]+(\.[a-z0-9]+)*$",
    )

    description: str = Field(
        ...,
        description="Human-readable explanation of the precondition.",
    )

    expr: str = Field(
        ...,
        description="Deterministic boolean expression evaluated against the state snapshot.",
    )


class ActionEffects(ModelBase):
    """
    Declarative description of which parts of state may change.
    """

    may_change: list[str] = Field(
        ...,
        description="List of state paths that this action may modify.",
    )


class ActionDeclaration(ModelBase):
    """
    Declarative definition of an action that may mutate application state.
    """

    action_id: ActionId = Field(
        ...,
        description="Stable identifier for the action.",
        pattern=r"^[a-z0-9]+(\.[a-z0-9]+)*$",
    )

    title: str = Field(
        ...,
        description="Short human-readable label for the action.",
    )

    description: str = Field(
        ...,
        description="Detailed explanation of what the action does.",
    )

    targets: list[ComponentId] = Field(
        ...,
        description="List of component IDs affected by this action.",
        min_length=1,
    )

    input_schema: dict[str, Any] = Field(
        ...,
        description="JSON Schema describing the inputs required to execute the action.",
    )

    preconditions: list[ActionPrecondition] = Field(
        default_factory=list,
        description="Conditions that must be satisfied before the action may execute.",
    )

    effects: ActionEffects = Field(
        ...,
        description="Declarative description of state changes caused by this action.",
    )

    permission: ActionPermission = Field(
        ...,
        description="Permission and risk metadata governing execution.",
    )


class ActionPermission(ModelBase):
    ...
    cost: int = Field(
        default=1,
        description="Abstract execution cost units consumed by this action",
    )
