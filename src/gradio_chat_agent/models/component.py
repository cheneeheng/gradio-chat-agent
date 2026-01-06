from typing import Any

from pydantic import Field

from .base import ComponentId, ModelBase


class ComponentPermissions(ModelBase):
    """
    Access rules governing how the agent may interact with a component.
    """

    readable: bool = Field(
        True,
        description="Whether the agent may read this component’s state.",
    )

    writable_via_actions_only: bool = Field(
        True,
        description="Must always be true; component state may only be mutated via actions.",
    )


class ComponentDeclaration(ModelBase):
    """
    Declarative definition of a UI component exposed to the chat agent.
    """

    component_id: ComponentId = Field(
        ...,
        description="Stable identifier for the component, used by actions and state snapshots.",
        pattern=r"^[a-z0-9]+(\.[a-z0-9]+)*$",
    )

    title: str = Field(
        ...,
        description="Short human-readable name of the component.",
    )

    description: str = Field(
        ...,
        description="Detailed explanation of the component’s purpose and behavior.",
    )

    state_schema: dict[str, Any] = Field(
        ...,
        description="JSON Schema describing the shape and constraints of the component state.",
    )

    permissions: ComponentPermissions = Field(
        ...,
        description="Access rules governing how the agent may observe or affect this component.",
    )

    invariants: list[str] = Field(
        default_factory=list,
        description="Human-readable invariants that must always hold for this component.",
    )

    tags: list[str] = Field(
        default_factory=list,
        description="Optional tags for categorization or filtering.",
    )
