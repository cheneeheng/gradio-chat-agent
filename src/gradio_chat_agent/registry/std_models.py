"""Standard model and inference actions and components.

This module implements the standard suite for model selection and inference,
including components for the selector, prompt editor, and output panel.
"""

from typing import Any

from gradio_chat_agent.models.action import (
    ActionDeclaration,
    ActionEffects,
    ActionPermission,
    ActionPrecondition,
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


# --- Components ---

MODEL_SELECTOR_ID = "model.selector"
PROMPT_EDITOR_ID = "prompt.editor"
OUTPUT_PANEL_ID = "output.panel"

model_selector_component = ComponentDeclaration(
    component_id=MODEL_SELECTOR_ID,
    title="Model Selector",
    description="Manages model selection and loading status.",
    state_schema={
        "type": "object",
        "properties": {
            "selected_model": {"type": ["string", "null"]},
            "loaded": {"type": "boolean"},
            "available_models": {
                "type": "array",
                "items": {"type": "string"}
            }
        },
        "required": ["selected_model", "loaded", "available_models"],
    },
    permissions=ComponentPermissions(
        readable=True, writable_via_actions_only=True
    ),
    tags=["std", "model"],
)

prompt_editor_component = ComponentDeclaration(
    component_id=PROMPT_EDITOR_ID,
    title="Prompt Editor",
    description="Captures the input prompt for inference.",
    state_schema={
        "type": "object",
        "properties": {
            "text": {"type": "string"},
            "last_updated": {"type": "string", "format": "date-time"}
        },
        "required": ["text"],
    },
    permissions=ComponentPermissions(
        readable=True, writable_via_actions_only=True
    ),
    tags=["std", "inference"],
)

output_panel_component = ComponentDeclaration(
    component_id=OUTPUT_PANEL_ID,
    title="Output Panel",
    description="Displays the result of the inference.",
    state_schema={
        "type": "object",
        "properties": {
            "latest_response": {"type": ["string", "null"]},
            "streaming": {"type": "boolean"},
            "tokens_used": {"type": "integer"}
        },
        "required": ["latest_response", "streaming", "tokens_used"],
    },
    permissions=ComponentPermissions(
        readable=True, writable_via_actions_only=True
    ),
    tags=["std", "inference"],
)


# --- Handlers ---

def select_model_handler(inputs: dict[str, Any], snapshot: StateSnapshot):
    model_name = inputs["model_name"]
    new_comps = snapshot.components.copy()
    state = new_comps.get(MODEL_SELECTOR_ID, {
        "selected_model": None,
        "loaded": False,
        "available_models": ["gpt-4o", "gpt-4o-mini", "claude-3-5-sonnet"]
    }).copy()

    state["selected_model"] = model_name
    state["loaded"] = False # Reset loaded when model changes
    new_comps[MODEL_SELECTOR_ID] = state

    diff = [
        StateDiffEntry(path=f"{MODEL_SELECTOR_ID}.selected_model", op=StateDiffOp.REPLACE, value=model_name),
        StateDiffEntry(path=f"{MODEL_SELECTOR_ID}.loaded", op=StateDiffOp.REPLACE, value=False)
    ]
    return new_comps, diff, f"Model selected: {model_name}"


def load_model_handler(inputs: dict[str, Any], snapshot: StateSnapshot):
    new_comps = snapshot.components.copy()
    state = new_comps.get(MODEL_SELECTOR_ID).copy()
    model_name = state["selected_model"]

    state["loaded"] = True
    new_comps[MODEL_SELECTOR_ID] = state

    diff = [
        StateDiffEntry(path=f"{MODEL_SELECTOR_ID}.loaded", op=StateDiffOp.REPLACE, value=True)
    ]
    return new_comps, diff, f"Model {model_name} loaded successfully."


def run_inference_handler(inputs: dict[str, Any], snapshot: StateSnapshot):
    prompt_text = inputs.get("prompt_override") or snapshot.components.get(PROMPT_EDITOR_ID, {}).get("text", "")
    
    new_comps = snapshot.components.copy()
    
    # Simulate inference result
    response = f"Simulated response for: {prompt_text[:20]}..."
    
    output_state = new_comps.get(OUTPUT_PANEL_ID, {
        "latest_response": None,
        "streaming": False,
        "tokens_used": 0
    }).copy()
    
    output_state["latest_response"] = response
    output_state["tokens_used"] += len(response.split()) # Mock token count
    new_comps[OUTPUT_PANEL_ID] = output_state
    
    diff = [
        StateDiffEntry(path=f"{OUTPUT_PANEL_ID}.latest_response", op=StateDiffOp.REPLACE, value=response),
        StateDiffEntry(path=f"{OUTPUT_PANEL_ID}.tokens_used", op=StateDiffOp.REPLACE, value=output_state["tokens_used"])
    ]
    return new_comps, diff, "Inference completed successfully."


# --- Actions ---

select_model_action = ActionDeclaration(
    action_id="model.select",
    title="Select Model",
    description="Select a model from the available list.",
    targets=[MODEL_SELECTOR_ID],
    input_schema={
        "type": "object",
        "properties": {
            "model_name": {"type": "string"}
        },
        "required": ["model_name"],
    },
    preconditions=[
        ActionPrecondition(
            id="check.model.exists",
            description="Model must be in available models.",
            expr="inputs['model_name'] in state['model.selector']['available_models']"
        )
    ],
    effects=ActionEffects(may_change=[f"{MODEL_SELECTOR_ID}.selected_model", f"{MODEL_SELECTOR_ID}.loaded"]),
    permission=ActionPermission(
        confirmation_required=False,
        risk=ActionRisk.LOW,
        visibility=ActionVisibility.USER,
    ),
)

load_model_action = ActionDeclaration(
    action_id="model.load",
    title="Load Model",
    description="Load the currently selected model into memory.",
    targets=[MODEL_SELECTOR_ID],
    input_schema={"type": "object"},
    preconditions=[
        ActionPrecondition(
            id="check.model.selected",
            description="A model must be selected first.",
            expr="state['model.selector']['selected_model'] is not None"
        )
    ],
    effects=ActionEffects(may_change=[f"{MODEL_SELECTOR_ID}.loaded"]),
    permission=ActionPermission(
        confirmation_required=False,
        risk=ActionRisk.MEDIUM,
        visibility=ActionVisibility.USER,
    ),
)

run_inference_action = ActionDeclaration(
    action_id="inference.run",
    title="Run Inference",
    description="Execute inference using the loaded model.",
    targets=[PROMPT_EDITOR_ID, OUTPUT_PANEL_ID],
    input_schema={
        "type": "object",
        "properties": {
            "prompt_override": {"type": "string"},
            "max_tokens": {"type": "integer", "default": 100}
        }
    },
    preconditions=[
        ActionPrecondition(
            id="check.model.loaded",
            description="Model must be loaded before running inference.",
            expr="state['model.selector']['loaded'] is True"
        )
    ],
    effects=ActionEffects(may_change=[f"{OUTPUT_PANEL_ID}.latest_response", f"{OUTPUT_PANEL_ID}.tokens_used"]),
    permission=ActionPermission(
        confirmation_required=False,
        risk=ActionRisk.MEDIUM,
        visibility=ActionVisibility.USER,
    ),
)
