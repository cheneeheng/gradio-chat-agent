"""System actions and components for session memory management.

This module defines the 'sys.memory' component and its associated action
handlers (remember, forget) which allow the agent to persist and retrieve
facts during a chat session.
"""

from typing import Any

from gradio_chat_agent.models.action import (
    ActionDeclaration,
    ActionEffects,
    ActionPermission,
)
from gradio_chat_agent.models.component import (
    ComponentDeclaration,
    ComponentPermissions,
)
from gradio_chat_agent.models.enums import (
    ActionRisk,
    ActionVisibility,
    StateDiffOp,
)
from gradio_chat_agent.models.execution_result import StateDiffEntry
from gradio_chat_agent.models.state_snapshot import StateSnapshot


# --- Component Definition ---

MEMORY_COMPONENT_ID = "sys.memory"

memory_component = ComponentDeclaration(
    component_id=MEMORY_COMPONENT_ID,
    title="Session Memory",
    description="Stores shared facts and context for the agent across the project session.",
    state_schema={
        "type": "object",
        "description": "Key-value store for facts.",
        "additionalProperties": True,
    },
    permissions=ComponentPermissions(
        readable=True, writable_via_actions_only=True
    ),
    tags=["system", "memory"],
)


# --- Action Handlers ---


def remember_handler(
    inputs: dict[str, Any], snapshot: StateSnapshot
) -> tuple[dict[str, dict[str, Any]], list[StateDiffEntry], str]:
    """Saves a fact into the system memory component.

    Args:
        inputs: Dictionary containing 'key' and 'value' to remember.
        snapshot: The current state snapshot.

    Returns:
        A tuple of (new_components_dict, list_of_diffs, summary_message).
    """
    key = inputs["key"]
    value = inputs["value"]

    # Get current components
    new_components = snapshot.components.copy()

    # Get or init memory state
    memory_state = new_components.get(MEMORY_COMPONENT_ID, {}).copy()

    # Update
    old_value = memory_state.get(key)
    memory_state[key] = value

    new_components[MEMORY_COMPONENT_ID] = memory_state

    # Diff
    diff = [
        StateDiffEntry(
            path=f"{MEMORY_COMPONENT_ID}.{key}",
            op=StateDiffOp.REPLACE
            if old_value is not None
            else StateDiffOp.ADD,
            value=value,
        )
    ]

    return new_components, diff, f"Remembered: {key} = {value}"


def forget_handler(
    inputs: dict[str, Any], snapshot: StateSnapshot
) -> tuple[dict[str, dict[str, Any]], list[StateDiffEntry], str]:
    """Removes a fact from the system memory component.

    Args:
        inputs: Dictionary containing the 'key' to forget.
        snapshot: The current state snapshot.

    Returns:
        A tuple of (new_components_dict, list_of_diffs, summary_message).
    """
    key = inputs["key"]

    new_components = snapshot.components.copy()
    memory_state = new_components.get(MEMORY_COMPONENT_ID, {}).copy()

    if key in memory_state:
        del memory_state[key]
        op = StateDiffOp.REMOVE
        msg = f"Forgot: {key}"
    else:
        op = None
        msg = f"Key not found: {key}"

    new_components[MEMORY_COMPONENT_ID] = memory_state

    diff = []
    if op:
        diff.append(
            StateDiffEntry(
                path=f"{MEMORY_COMPONENT_ID}.{key}", op=op, value=None
            )
        )

    return new_components, diff, msg


# --- Action Declarations ---

remember_action = ActionDeclaration(
    action_id="memory.remember",
    title="Remember Fact",
    description="Save a piece of information to project memory.",
    targets=[MEMORY_COMPONENT_ID],
    input_schema={
        "type": "object",
        "properties": {
            "key": {"type": "string"},
            "value": {
                "type": ["string", "number", "boolean", "object", "array"]
            },
        },
        "required": ["key", "value"],
    },
    preconditions=[],
    effects=ActionEffects(may_change=[f"{MEMORY_COMPONENT_ID}.*"]),
    permission=ActionPermission(
        confirmation_required=False,
        risk=ActionRisk.LOW,
        visibility=ActionVisibility.DEVELOPER,
    ),
)

forget_action = ActionDeclaration(
    action_id="memory.forget",
    title="Forget Fact",
    description="Remove a piece of information from project memory.",
    targets=[MEMORY_COMPONENT_ID],
    input_schema={
        "type": "object",
        "properties": {"key": {"type": "string"}},
        "required": ["key"],
    },
    preconditions=[],
    effects=ActionEffects(may_change=[f"{MEMORY_COMPONENT_ID}.*"]),
    permission=ActionPermission(
        confirmation_required=False,
        risk=ActionRisk.LOW,
        visibility=ActionVisibility.DEVELOPER,
    ),
)
