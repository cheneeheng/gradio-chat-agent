"""Web automation components and actions.

This module provides a virtual browser component and actions for navigating,
clicking, and typing on web pages using Playwright.
"""

from typing import Any, Optional

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
BROWSER_ID = "browser"

browser_component = ComponentDeclaration(
    component_id=BROWSER_ID,
    title="Web Browser",
    description="A virtual browser for web automation and information retrieval.",
    state_schema={
        "type": "object",
        "properties": {
            "url": {"type": "string"},
            "title": {"type": "string"},
            "status": {"type": "string", "enum": ["idle", "busy", "error"]},
            "last_error": {"type": ["string", "null"]},
            "pending_action": {
                "type": ["object", "null"],
                "properties": {
                    "type": {"type": "string"},
                    "params": {"type": "object"}
                }
            },
            "last_action_result": {"type": ["string", "null"]}
        },
        "required": ["status"],
    },
    permissions=ComponentPermissions(
        readable=True, writable_via_actions_only=True
    ),
    tags=["automation", "web"],
)

# --- Handlers ---

def _create_pending_action_handler(action_type: str):
    def handler(inputs: dict[str, Any], snapshot: StateSnapshot):
        new_comps = snapshot.components.copy()
        state = new_comps.get(BROWSER_ID, {
            "url": "about:blank",
            "title": "",
            "status": "idle",
            "last_error": None,
            "pending_action": None,
            "last_action_result": None
        }).copy()

        state["status"] = "busy"
        state["pending_action"] = {
            "type": action_type,
            "params": inputs
        }
        new_comps[BROWSER_ID] = state

        diff = [
            StateDiffEntry(path=f"{BROWSER_ID}.status", op=StateDiffOp.REPLACE, value="busy"),
            StateDiffEntry(path=f"{BROWSER_ID}.pending_action", op=StateDiffOp.REPLACE, value=state["pending_action"])
        ]
        return new_comps, diff, f"Browser action '{action_type}' queued."
    
    return handler

navigate_handler = _create_pending_action_handler("navigate")
click_handler = _create_pending_action_handler("click")
type_handler = _create_pending_action_handler("type")
scroll_handler = _create_pending_action_handler("scroll")

def sync_browser_state_handler(inputs: dict[str, Any], snapshot: StateSnapshot):
    """Internal handler to sync the real browser state back to the component."""
    new_comps = snapshot.components.copy()
    state = new_comps.get(BROWSER_ID, {}).copy()

    for key in ["url", "title", "status", "last_error", "last_action_result"]:
        if key in inputs:
            state[key] = inputs[key]
    
    state["pending_action"] = None # Clear pending action
    new_comps[BROWSER_ID] = state

    diff = []
    for key, val in inputs.items():
        diff.append(StateDiffEntry(path=f"{BROWSER_ID}.{key}", op=StateDiffOp.REPLACE, value=val))
    diff.append(StateDiffEntry(path=f"{BROWSER_ID}.pending_action", op=StateDiffOp.REPLACE, value=None))

    return new_comps, diff, "Browser state synchronized."


# --- Actions ---

navigate_action = ActionDeclaration(
    action_id="browser.navigate",
    title="Navigate",
    description="Navigate to a specific URL.",
    targets=[BROWSER_ID],
    input_schema={
        "type": "object",
        "properties": {
            "url": {"type": "string", "format": "uri"}
        },
        "required": ["url"],
    },
    permission=ActionPermission(
        confirmation_required=False,
        risk=ActionRisk.MEDIUM,
        visibility=ActionVisibility.USER,
    ),
    cost=2.0
)

click_action = ActionDeclaration(
    action_id="browser.click",
    title="Click Element",
    description="Click an element on the page using a CSS selector.",
    targets=[BROWSER_ID],
    input_schema={
        "type": "object",
        "properties": {
            "selector": {"type": "string"}
        },
        "required": ["selector"],
    },
    permission=ActionPermission(
        confirmation_required=False,
        risk=ActionRisk.MEDIUM,
        visibility=ActionVisibility.USER,
    ),
    cost=1.5
)

type_action = ActionDeclaration(
    action_id="browser.type",
    title="Type Text",
    description="Type text into an input field.",
    targets=[BROWSER_ID],
    input_schema={
        "type": "object",
        "properties": {
            "selector": {"type": "string"},
            "text": {"type": "string"}
        },
        "required": ["selector", "text"],
    },
    permission=ActionPermission(
        confirmation_required=False,
        risk=ActionRisk.MEDIUM,
        visibility=ActionVisibility.USER,
    ),
    cost=1.5
)

scroll_action = ActionDeclaration(
    action_id="browser.scroll",
    title="Scroll",
    description="Scroll the page.",
    targets=[BROWSER_ID],
    input_schema={
        "type": "object",
        "properties": {
            "direction": {"type": "string", "enum": ["up", "down"]},
            "amount": {"type": "integer", "default": 500}
        },
        "required": ["direction"],
    },
    permission=ActionPermission(
        confirmation_required=False,
        risk=ActionRisk.LOW,
        visibility=ActionVisibility.USER,
    ),
    cost=0.5
)

sync_browser_state_action = ActionDeclaration(
    action_id="browser.sync.state",
    title="Sync State",
    description="Internal action to sync browser state.",
    targets=[BROWSER_ID],
    input_schema={
        "type": "object",
        "properties": {
            "url": {"type": "string"},
            "title": {"type": "string"},
            "status": {"type": "string"},
            "last_error": {"type": ["string", "null"]},
            "last_action_result": {"type": ["string", "null"]}
        }
    },
    permission=ActionPermission(
        confirmation_required=False,
        risk=ActionRisk.LOW,
        visibility=ActionVisibility.DEVELOPER,
    ),
)
