import gradio as gr
import json
import uuid
from typing import Any

from gradio_chat_agent.execution.engine import ExecutionEngine
from gradio_chat_agent.chat.adapter import AgentAdapter
from gradio_chat_agent.models.intent import ChatIntent
from gradio_chat_agent.models.enums import ExecutionMode, IntentType

DEFAULT_PROJECT_ID = "default_project"
DEFAULT_USER_ID = "admin_user"


def create_ui(engine: ExecutionEngine, adapter: AgentAdapter) -> gr.Blocks:
    """Constructs the Gradio UI."""

    with gr.Blocks(title="Gradio Chat Agent") as demo:
        # State variables
        project_id_state = gr.State(DEFAULT_PROJECT_ID)
        user_id_state = gr.State(DEFAULT_USER_ID)
        # History format: list of [user_msg, bot_msg] or compatible with Chatbot
        history_state = gr.State([]) 
        
        with gr.Row():
            # --- Left Sidebar ---
            with gr.Column(scale=1, min_width=250):
                gr.Markdown("### Control Panel")
                project_selector = gr.Dropdown(
                    choices=[DEFAULT_PROJECT_ID], 
                    value=DEFAULT_PROJECT_ID, 
                    label="Project"
                )
                execution_mode = gr.Radio(
                    choices=[e.value for e in ExecutionMode],
                    value=ExecutionMode.ASSISTED.value,
                    label="Execution Mode"
                )
                user_info = gr.Markdown(f"**User:** {DEFAULT_USER_ID} (Admin)")
                
                reset_btn = gr.Button("Reset State (Debug)", variant="secondary")

            # --- Main Chat Area ---
            with gr.Column(scale=2):
                chatbot = gr.Chatbot(
                    label="Agent",
                    height=600,
                    type="messages" # New Gradio format: list of dicts {'role': 'user', 'content': '...'}
                )
                msg_input = gr.Textbox(
                    placeholder="Type a command...",
                    label="Command",
                    lines=2
                )
                submit_btn = gr.Button("Submit", variant="primary")
                
                # Plan Preview (Hidden by default)
                with gr.Group(visible=False) as plan_group:
                    gr.Markdown("### Proposed Plan")
                    plan_display = gr.Markdown("No plan pending.")
                    with gr.Row():
                        approve_plan_btn = gr.Button("Approve Plan", variant="primary")
                        reject_plan_btn = gr.Button("Reject Plan", variant="stop")

            # --- Right State Inspector ---
            with gr.Column(scale=1, min_width=300):
                gr.Markdown("### State Inspector")
                
                with gr.Tabs():
                    with gr.Tab("Live State"):
                        state_json = gr.JSON(label="Current State")
                    with gr.Tab("Diffs"):
                        diff_json = gr.JSON(label="Last Action Diff")
                    with gr.Tab("Registry"):
                        registry_json = gr.JSON(label="Available Actions")

        # --- Event Handlers ---

        def fetch_state(pid):
            snapshot = engine.repository.get_latest_snapshot(pid)
            if snapshot:
                return snapshot.components
            return {}

        def refresh_ui(pid):
            state = fetch_state(pid)
            # Registry info
            reg_info = {
                "components": [c.component_id for c in engine.registry.list_components()],
                "actions": [a.action_id for a in engine.registry.list_actions()]
            }
            return state, {},
            reg_info

        # Initial Load
        demo.load(refresh_ui, inputs=[project_id_state], outputs=[state_json, diff_json, registry_json])

        # Chat Interaction
        def on_submit(message, history, pid, mode):
            # 1. Add user message to history
            new_history = history + [{"role": "user", "content": message}]
            
            # 2. Fetch context
            snapshot = engine.repository.get_latest_snapshot(pid)
            if not snapshot:
                # Should not happen if initialized, but handle it
                from gradio_chat_agent.models.state_snapshot import StateSnapshot
                snapshot = StateSnapshot(snapshot_id="init", components={})
                
            state_dict = snapshot.components
            comp_reg = {c.component_id: c.model_dump() for c in engine.registry.list_components()}
            act_reg = {a.action_id: a.model_dump() for a in engine.registry.list_actions()}
            
            # 3. Call Agent
            # Convert history to format expected by adapter (list of dicts) if needed
            # Gradio 'messages' type is already [{'role': 'user', 'content': ''}...]
            
            try:
                result = adapter.message_to_intent_or_plan(
                    message=message,
                    history=new_history,
                    state_snapshot=state_dict,
                    component_registry=comp_reg,
                    action_registry=act_reg,
                    execution_mode=mode
                )
            except Exception as e:
                err_msg = f"Agent Error: {str(e)}"
                new_history.append({"role": "assistant", "content": err_msg})
                return "", new_history, state_dict, {"error": str(e)}

            # 4. Handle Result
            if isinstance(result, ChatIntent):
                intent = result
                if intent.type == IntentType.CLARIFICATION_REQUEST:
                     new_history.append({"role": "assistant", "content": intent.question})
                     return "", new_history, state_dict, {}
                
                elif intent.type == IntentType.ACTION_CALL:
                    # Execute!
                    # For MVP, we assume confirmed=True if mode is Autonomous, else...
                    # Wait, docs say "Chat UI... Never executes actions directly" -> Agent Proposes.
                    # But the flow in 02_GETTING_STARTED says "Set counter to 5" -> "Engine applies action".
                    
                    # If mode is INTERACTIVE, we should technically ask for confirmation for EVERYTHING?
                    # Or just rely on 'confirmation_required' flag?
                    
                    # Let's try to execute.
                    exec_result = engine.execute_intent(pid, intent, user_roles=["admin"])
                    
                    if exec_result.status == "success":
                        resp = f"Executed `{intent.action_id}`.\n\nResult: {exec_result.message}"
                        new_history.append({"role": "assistant", "content": resp})
                        
                        # Fetch new state
                        new_snapshot = engine.repository.get_latest_snapshot(pid)
                        new_state = new_snapshot.components if new_snapshot else {}
                        return "", new_history, new_state, exec_result.state_diff
                    
                    elif exec_result.error and exec_result.error.code == "confirmation_required":
                         # Special flow for confirmation
                         # We could present a button. For now, just text.
                         resp = f"Action `{intent.action_id}` requires confirmation. Please type 'confirm' to proceed."
                         # We need to STORE this intent in pending state?
                         # For MVP, just let user retry saying "confirm set counter to 5" (Agent handles it?)
                         new_history.append({"role": "assistant", "content": resp})
                         return "", new_history, state_dict, {}
                    
                    else:
                        resp = f"Action Failed/Rejected: {exec_result.message}"
                        new_history.append({"role": "assistant", "content": resp})
                        return "", new_history, state_dict, {}

            else:
                # Plan logic (skip for now or basic msg)
                new_history.append({"role": "assistant", "content": "Multi-step plans not fully implemented in UI yet."})
                return "", new_history, state_dict, {}


        submit_btn.click(
            on_submit,
            inputs=[msg_input, chatbot, project_id_state, execution_mode],
            outputs=[msg_input, chatbot, state_json, diff_json]
        )
        
        msg_input.submit(
            on_submit,
            inputs=[msg_input, chatbot, project_id_state, execution_mode],
            outputs=[msg_input, chatbot, state_json, diff_json]
        )

    return demo
