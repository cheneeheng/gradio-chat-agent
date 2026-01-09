"""Data models for defining UI components.

This module defines the schema for registering components that the chat agent
can observe and manipulate.
"""

from typing import Any, Literal

from pydantic import BaseModel, Field


class ComponentPermissions(BaseModel):
    """Access rules for a component.

    Attributes:
        readable: Whether the agent can read the component's state.
        writable_via_actions_only: Enforces that state changes must happen
            through actions (always True).
    """

    readable: bool = Field(
        ..., description="Whether the agent can read the component's state."
    )
    writable_via_actions_only: Literal[True] = Field(
        default=True,
        description=(
            "Enforces that state changes must happen through actions (always True)."
        ),
    )


class ComponentDeclaration(BaseModel):
    """Complete definition of a registered UI component.

    Attributes:
        component_id: Unique, dot-notation identifier (e.g., 'demo.counter').
        title: Short human-readable name.
        description: Explanation of the component's purpose.
        state_schema: JSON Schema describing the component's state structure.
        permissions: Access control rules.
        invariants: List of natural language invariants for the component.
        tags: Optional categorization tags.
    """

    component_id: str = Field(
        ...,
        pattern=r"^[a-z0-9]+(\.[a-z0-9]+)*$",
        description="Unique, dot-notation identifier (e.g., 'demo.counter').",
    )
    title: str = Field(..., description="Short human-readable name.")
    description: str = Field(
        ..., description="Explanation of the component's purpose."
    )
    state_schema: dict[str, Any] = Field(
        ...,
        description="JSON Schema describing the component's state structure.",
    )
    permissions: ComponentPermissions = Field(
        ..., description="Access control rules."
    )
    invariants: list[str] = Field(
        default_factory=list,
        description="List of natural language invariants for the component.",
    )
    tags: list[str] = Field(
        default_factory=list, description="Optional categorization tags."
    )
