"""Standard library components and actions for the Gradio Chat Agent.

This module provides a set of reusable UI components and actions in the 'std' 
namespace to provide a consistent base for all projects.
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


# --- Component IDs ---
TEXT_INPUT_ID = "std.text.input"
SLIDER_ID = "std.slider"
STATUS_INDICATOR_ID = "std.status.indicator"


# --- Components ---

text_input_component = ComponentDeclaration(
    component_id=TEXT_INPUT_ID,
    title="Text Input",
    description="A simple text input field.",
    state_schema={
        "type": "object",
        "properties": {
            "value": {"type": "string"},
            "placeholder": {"type": "string"},
            "label": {"type": "string"}
        },
        "required": ["value"],
    },
    permissions=ComponentPermissions(
        readable=True, writable_via_actions_only=True
    ),
    tags=["std", "input"],
)

slider_component = ComponentDeclaration(
    component_id=SLIDER_ID,
    title="Slider",
    description="A numerical slider component.",
    state_schema={
        "type": "object",
        "properties": {
            "value": {"type": "number"},
            "min": {"type": "number"},
            "max": {"type": "number"},
            "step": {"type": "number"},
            "label": {"type": "string"}
        },
        "required": ["value", "min", "max"],
    },
    permissions=ComponentPermissions(
        readable=True, writable_via_actions_only=True
    ),
    tags=["std", "input"],
)

status_indicator_component = ComponentDeclaration(
    component_id=STATUS_INDICATOR_ID,
    title="Status Indicator",
    description="Displays a status message and color.",
    state_schema={
        "type": "object",
        "properties": {
            "status": {"type": "string", "enum": ["online", "offline", "busy", "away"]},
            "message": {"type": "string"},
            "last_updated": {"type": "string", "format": "date-time"}
        },
        "required": ["status"],
    },
    permissions=ComponentPermissions(
        readable=True, writable_via_actions_only=True
    ),
    tags=["std", "display"],
)


# --- Handlers ---

def text_input_set_handler(inputs: dict[str, Any], snapshot: StateSnapshot):
    new_value = inputs["value"]
    new_comps = snapshot.components.copy()
    
    comp_state = new_comps.get(TEXT_INPUT_ID, {"value": ""}).copy()
    comp_state["value"] = new_value
    new_comps[TEXT_INPUT_ID] = comp_state

    diff = [
        StateDiffEntry(path=f"{TEXT_INPUT_ID}.value", op=StateDiffOp.REPLACE, value=new_value)
    ]
    return new_comps, diff, f"Text input set to: {new_value}"


def slider_set_handler(inputs: dict[str, Any], snapshot: StateSnapshot):
    new_value = inputs["value"]
    new_comps = snapshot.components.copy()
    
    comp_state = new_comps.get(SLIDER_ID, {"value": 0, "min": 0, "max": 100}).copy()
    comp_state["value"] = new_value
    new_comps[SLIDER_ID] = comp_state

    diff = [
        StateDiffEntry(path=f"{SLIDER_ID}.value", op=StateDiffOp.REPLACE, value=new_value)
    ]
    return new_comps, diff, f"Slider set to: {new_value}"


def status_indicator_update_handler(inputs: dict[str, Any], snapshot: StateSnapshot):
    new_status = inputs.get("status")
    new_message = inputs.get("message")
    
    new_comps = snapshot.components.copy()
    comp_state = new_comps.get(STATUS_INDICATOR_ID, {"status": "offline"}).copy()
    
    if new_status:
        comp_state["status"] = new_status
    if new_message is not None:
        comp_state["message"] = new_message
        
    import datetime
    comp_state["last_updated"] = datetime.datetime.now().isoformat()
    new_comps[STATUS_INDICATOR_ID] = comp_state

    diff = []
    if new_status:
        diff.append(StateDiffEntry(path=f"{STATUS_INDICATOR_ID}.status", op=StateDiffOp.REPLACE, value=new_status))
    if new_message is not None:
        diff.append(StateDiffEntry(path=f"{STATUS_INDICATOR_ID}.message", op=StateDiffOp.REPLACE, value=new_message))
    
    return new_comps, diff, f"Status updated to: {new_status or comp_state['status']}"


# --- Actions ---

text_input_set_action = ActionDeclaration(
    action_id="std.text.input.set",
    title="Set Text",
    description="Set the value of the text input.",
    targets=[TEXT_INPUT_ID],
    input_schema={
        "type": "object",
        "properties": {"value": {"type": "string"}},
        "required": ["value"],
    },
    effects=ActionEffects(may_change=[f"{TEXT_INPUT_ID}.value"]),
    permission=ActionPermission(
        confirmation_required=False,
        risk=ActionRisk.LOW,
        visibility=ActionVisibility.USER,
    ),
)

slider_set_action = ActionDeclaration(
    action_id="std.slider.set",
    title="Set Slider Value",
    description="Set the value of the slider.",
    targets=[SLIDER_ID],
    input_schema={
        "type": "object",
        "properties": {"value": {"type": "number"}},
        "required": ["value"],
    },
    effects=ActionEffects(may_change=[f"{SLIDER_ID}.value"]),
    permission=ActionPermission(
        confirmation_required=False,
        risk=ActionRisk.LOW,
        visibility=ActionVisibility.USER,
    ),
)

status_indicator_update_action = ActionDeclaration(
    action_id="std.status.indicator.update",
    title="Update Status",
    description="Update the status indicator and optional message.",
    targets=[STATUS_INDICATOR_ID],
    input_schema={
        "type": "object",
        "properties": {
            "status": {"type": "string", "enum": ["online", "offline", "busy", "away"]},
            "message": {"type": "string"}
        }
    },
    effects=ActionEffects(may_change=[f"{STATUS_INDICATOR_ID}.status", f"{STATUS_INDICATOR_ID}.message", f"{STATUS_INDICATOR_ID}.last_updated"]),
    permission=ActionPermission(
        confirmation_required=False,
        risk=ActionRisk.LOW,
        visibility=ActionVisibility.USER,
    ),
)