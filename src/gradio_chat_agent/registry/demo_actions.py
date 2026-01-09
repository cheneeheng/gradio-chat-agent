"""Demo actions and components for the Gradio Chat Agent.

This module provides a simple counter component and its associated action
handlers (set, increment, reset) to demonstrate the core execution flow.
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


# --- Component ---
COUNTER_ID = "demo.counter"

counter_component = ComponentDeclaration(
    component_id=COUNTER_ID,
    title="Demo Counter",
    description="A simple integer counter for demonstration purposes.",
    state_schema={
        "type": "object",
        "properties": {"value": {"type": "integer"}},
        "required": ["value"],
    },
    permissions=ComponentPermissions(
        readable=True, writable_via_actions_only=True
    ),
    tags=["demo"],
)

# --- Handlers ---


def set_handler(inputs: dict[str, Any], snapshot: StateSnapshot):
    """Sets the counter to a specific value.

    Args:
        inputs: Dictionary containing the 'value' to set.
        snapshot: The current state snapshot.

    Returns:
        A tuple of (new_components_dict, list_of_diffs, summary_message).
    """
    val = inputs["value"]
    new_comps = snapshot.components.copy()
    old_val = new_comps.get(COUNTER_ID, {}).get("value", 0)

    new_comps[COUNTER_ID] = {"value": val}

    diff = [
        StateDiffEntry(
            path=f"{COUNTER_ID}.value", op=StateDiffOp.REPLACE, value=val
        )
    ]
    return new_comps, diff, f"Counter set to {val} (was {old_val})"


def increment_handler(inputs: dict[str, Any], snapshot: StateSnapshot):
    """Increments the counter by a given amount.

    Args:
        inputs: Dictionary containing the optional 'amount' to increment.
        snapshot: The current state snapshot.

    Returns:
        A tuple of (new_components_dict, list_of_diffs, summary_message).
    """
    amount = inputs.get("amount", 1)
    new_comps = snapshot.components.copy()
    old_val = new_comps.get(COUNTER_ID, {}).get("value", 0)
    new_val = old_val + amount

    new_comps[COUNTER_ID] = {"value": new_val}

    diff = [
        StateDiffEntry(
            path=f"{COUNTER_ID}.value", op=StateDiffOp.REPLACE, value=new_val
        )
    ]
    return new_comps, diff, f"Counter incremented by {amount} to {new_val}"


def reset_handler(inputs: dict[str, Any], snapshot: StateSnapshot):
    """Resets the counter to zero.

    Args:
        inputs: Empty dictionary.
        snapshot: The current state snapshot.

    Returns:
        A tuple of (new_components_dict, list_of_diffs, summary_message).
    """
    new_comps = snapshot.components.copy()
    new_comps[COUNTER_ID] = {"value": 0}

    diff = [
        StateDiffEntry(
            path=f"{COUNTER_ID}.value", op=StateDiffOp.REPLACE, value=0
        )
    ]
    return new_comps, diff, "Counter reset to 0"


# --- Actions ---

set_action = ActionDeclaration(
    action_id="demo.counter.set",
    title="Set Counter",
    description="Set the counter to a specific integer value.",
    targets=[COUNTER_ID],
    input_schema={
        "type": "object",
        "properties": {"value": {"type": "integer"}},
        "required": ["value"],
    },
    preconditions=[],
    effects=ActionEffects(may_change=[f"{COUNTER_ID}.value"]),
    permission=ActionPermission(
        confirmation_required=False,
        risk=ActionRisk.LOW,
        visibility=ActionVisibility.USER,
    ),
)

increment_action = ActionDeclaration(
    action_id="demo.counter.increment",
    title="Increment Counter",
    description="Increase the counter value by a given amount (default 1).",
    targets=[COUNTER_ID],
    input_schema={
        "type": "object",
        "properties": {"amount": {"type": "integer", "default": 1}},
    },
    preconditions=[],
    effects=ActionEffects(may_change=[f"{COUNTER_ID}.value"]),
    permission=ActionPermission(
        confirmation_required=False,
        risk=ActionRisk.LOW,
        visibility=ActionVisibility.USER,
    ),
)

reset_action = ActionDeclaration(
    action_id="demo.counter.reset",
    title="Reset Counter",
    description="Reset the counter to zero.",
    targets=[COUNTER_ID],
    input_schema={"type": "object"},
    preconditions=[],
    effects=ActionEffects(may_change=[f"{COUNTER_ID}.value"]),
    permission=ActionPermission(
        confirmation_required=True,
        risk=ActionRisk.MEDIUM,
        visibility=ActionVisibility.USER,
    ),
)
