"""UI layout and event handling for the Gradio Chat Agent.

This module defines the structural components of the Gradio interface and the
logic for handling user interactions, agent communication, and engine
execution.
"""

import gradio as gr

from gradio_chat_agent.api.endpoints import ApiEndpoints
from gradio_chat_agent.chat.adapter import AgentAdapter
from gradio_chat_agent.execution.engine import ExecutionEngine
from gradio_chat_agent.models.enums import ExecutionMode, IntentType
from gradio_chat_agent.models.intent import ChatIntent
from gradio_chat_agent.models.plan import ExecutionPlan
from gradio_chat_agent.utils import encode_media


DEFAULT_PROJECT_ID = "default_project"
DEFAULT_USER_ID = "admin_user"


def create_ui(engine: ExecutionEngine, adapter: AgentAdapter) -> gr.Blocks:
    """Constructs the Gradio UI and sets up event handlers.

    Args:
        engine: The authoritative execution engine for state mutations.
        adapter: The chat agent adapter for natural language interpretation.

    Returns:
        A Gradio gr.Blocks object containing the application layout.
    """
    api = ApiEndpoints(engine)

    with gr.Blocks(title="Gradio Chat Agent") as demo:
        # State variables
        project_id_state = gr.State(DEFAULT_PROJECT_ID)
        user_id_state = gr.State(DEFAULT_USER_ID)
        history_state = gr.State([])
        pending_plan_state = gr.State(None)

        with gr.Row():
            # --- Left Sidebar ---
            with gr.Column(scale=1, min_width=250):
                gr.Markdown("### Control Panel")
                project_selector = gr.Dropdown(
                    choices=[DEFAULT_PROJECT_ID],
                    value=DEFAULT_PROJECT_ID,
                    label="Project",
                )
                execution_mode = gr.Radio(
                    choices=[e.value for e in ExecutionMode],
                    value=ExecutionMode.ASSISTED.value,
                    label="Execution Mode",
                )
                user_info = gr.Markdown(f"**User:** {DEFAULT_USER_ID} (Admin)")

                reset_btn = gr.Button(
                    "Reset State (Debug)", variant="secondary"
                )

            # --- Main Chat Area ---
            with gr.Column(scale=2):
                chatbot = gr.Chatbot(label="Agent", height=600)
                msg_input = gr.MultimodalTextbox(
                    placeholder="Type a command or upload image...", label="Command", lines=2
                )
                submit_btn = gr.Button("Submit", variant="primary")

                # Plan Preview (Hidden by default)
                with gr.Group(visible=False) as plan_group:
                    gr.Markdown("### Proposed Plan")
                    plan_display = gr.Markdown("No plan pending.")
                    with gr.Row():
                        approve_plan_btn = gr.Button(
                            "Approve Plan", variant="primary"
                        )
                        reject_plan_btn = gr.Button(
                            "Reject Plan", variant="stop"
                        )

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
            """Internal helper to fetch latest state for a project."""
            snapshot = engine.repository.get_latest_snapshot(pid)
            if snapshot:
                return snapshot.components
            return {}

        def refresh_ui(pid):
            """Internal handler to refresh all UI components."""
            state = fetch_state(pid)
            # Registry info
            reg_info = {
                "components": [
                    c.component_id for c in engine.registry.list_components()
                ],
                "actions": [
                    a.action_id for a in engine.registry.list_actions()
                ],
            }
            return (
                state,
                {},
                reg_info,
            )

        # Initial Load
        demo.load(
            refresh_ui,
            inputs=[project_id_state],
            outputs=[state_json, diff_json, registry_json],
        )

        # Chat Interaction
        def on_submit(message_data, history, pid, uid, mode):
            """Main handler for chat message submission."""
            # Parse MultimodalTextbox input
            if isinstance(message_data, dict):
                message = message_data.get("text", "")
                files = message_data.get("files", [])
            else:
                message = str(message_data)
                files = []

            # 1. Add user message to history
            new_history = history + [{"role": "user", "content": message}]

            # 2. Fetch context
            snapshot = engine.repository.get_latest_snapshot(pid)
            if not snapshot:
                from gradio_chat_agent.models.state_snapshot import (
                    StateSnapshot,
                )

                snapshot = StateSnapshot(snapshot_id="init", components={})

            state_dict = snapshot.components
            facts = engine.repository.get_session_facts(pid, uid)
            
            comp_reg = {
                c.component_id: c.model_dump()
                for c in engine.registry.list_components()
            }
            act_reg = {
                a.action_id: a.model_dump()
                for a in engine.registry.list_actions()
            }

            # Media processing
            media = None
            if files:
                # Use the first file
                file_path = files[0]
                media = encode_media(file_path)
                media["type"] = "image" # Force image for now

            try:
                result = adapter.message_to_intent_or_plan(
                    message=message,
                    history=new_history,
                    state_snapshot=state_dict,
                    component_registry=comp_reg,
                    action_registry=act_reg,
                    execution_mode=mode,
                    facts=facts,
                    media=media,
                )
            except Exception as e:
                err_msg = f"Agent Error: {str(e)}"
                new_history.append({"role": "assistant", "content": err_msg})
                # Return empty plan/pending state
                return (
                    "",
                    new_history,
                    state_dict,
                    {"error": str(e)},
                    gr.update(),
                    gr.update(visible=False),
                    None,
                )

            # 4. Handle Result
            if isinstance(result, ExecutionPlan):
                # Handle Plan
                plan_md = f"## Proposed Plan (ID: {result.plan_id})\n"
                for i, step in enumerate(result.steps):
                    plan_md += (
                        f"{i + 1}. **{step.action_id}**: `{step.inputs}`\n"
                    )

                new_history.append(
                    {
                        "role": "assistant",
                        "content": "I have proposed a plan. Please review it below.",
                    }
                )

                return (
                    "",
                    new_history,
                    state_dict,
                    {},
                    plan_md,
                    gr.update(visible=True),
                    result,
                )

            elif isinstance(result, ChatIntent):
                intent = result
                if intent.type == IntentType.CLARIFICATION_REQUEST:
                    new_history.append(
                        {"role": "assistant", "content": intent.question}
                    )
                    return (
                        "",
                        new_history,
                        state_dict,
                        {},
                        "No plan pending.",
                        gr.update(visible=False),
                        None,
                    )

                elif intent.type == IntentType.ACTION_CALL:
                    # Execute single action
                    exec_result = engine.execute_intent(
                        pid, intent, user_roles=["admin"], user_id=uid
                    )

                    if exec_result.status == "success":
                        resp = f"Executed `{intent.action_id}`.\n\nResult: {exec_result.message}"
                        new_history.append(
                            {"role": "assistant", "content": resp}
                        )

                        new_snapshot = engine.repository.get_latest_snapshot(
                            pid
                        )
                        new_state = (
                            new_snapshot.components if new_snapshot else {}
                        )

                        return (
                            "",
                            new_history,
                            new_state,
                            exec_result.state_diff,
                            "No plan pending.",
                            gr.update(visible=False),
                            None,
                        )

                    elif (
                        exec_result.error
                        and exec_result.error.code == "confirmation_required"
                    ):
                        resp = f"Action `{intent.action_id}` requires confirmation. Please type 'confirm' to proceed."
                        new_history.append(
                            {"role": "assistant", "content": resp}
                        )
                        return (
                            "",
                            new_history,
                            state_dict,
                            {},
                            "No plan pending.",
                            gr.update(visible=False),
                            None,
                        )

                    else:
                        resp = f"Action Failed/Rejected: {exec_result.message}"
                        new_history.append(
                            {"role": "assistant", "content": resp}
                        )
                        return (
                            "",
                            new_history,
                            state_dict,
                            {},
                            "No plan pending.",
                            gr.update(visible=False),
                            None,
                        )

            return (
                "",
                new_history,
                state_dict,
                {},
                "No plan pending.",
                gr.update(visible=False),
                None,
            )

        submit_btn.click(
            on_submit,
            inputs=[msg_input, chatbot, project_id_state, user_id_state, execution_mode],
            outputs=[
                msg_input,
                chatbot,
                state_json,
                diff_json,
                plan_display,
                plan_group,
                pending_plan_state,
            ],
        )

        msg_input.submit(
            on_submit,
            inputs=[msg_input, chatbot, project_id_state, user_id_state, execution_mode],
            outputs=[
                msg_input,
                chatbot,
                state_json,
                diff_json,
                plan_display,
                plan_group,
                pending_plan_state,
            ],
        )

        # Plan Approval Handlers
        def on_approve_plan(plan, history, pid, uid):
            if not plan:
                return (
                    history,
                    {},
                    {},
                    "No plan",
                    gr.update(visible=False),
                    None,
                )

            results = engine.execute_plan(pid, plan, user_roles=["admin"], user_id=uid)

            summary = "### Plan Execution Result\n"
            final_diff = []
            for res in results:
                status_icon = "✅" if res.status == "success" else "❌"
                summary += (
                    f"- {status_icon} **{res.action_id}**: {res.message}\n"
                )
                if res.state_diff:
                    final_diff.extend(res.state_diff)

            history.append({"role": "assistant", "content": summary})

            snapshot = engine.repository.get_latest_snapshot(pid)
            new_state = snapshot.components if snapshot else {}

            return (
                history,
                new_state,
                final_diff,
                "Plan Executed.",
                gr.update(visible=False),
                None,
            )

        approve_plan_btn.click(
            on_approve_plan,
            inputs=[pending_plan_state, chatbot, project_id_state, user_id_state],
            outputs=[
                chatbot,
                state_json,
                diff_json,
                plan_display,
                plan_group,
                pending_plan_state,
            ],
        )

        def on_reject_plan(history):
            history.append({"role": "assistant", "content": "Plan rejected."})
            return history, "Plan rejected.", gr.update(visible=False), None

        reject_plan_btn.click(
            on_reject_plan,
            inputs=[chatbot],
            outputs=[chatbot, plan_display, plan_group, pending_plan_state],
        )

        # --- API Endpoints ---
        with gr.Group(visible=False):
            # execute_action
            api_project_id = gr.Textbox(label="project_id")
            api_action_id = gr.Textbox(label="action_id")
            api_inputs = gr.JSON(label="inputs")
            api_mode = gr.Textbox(label="mode")
            api_confirmed = gr.Checkbox(label="confirmed")
            api_result = gr.JSON(label="result")

            gr.Button("Execute API").click(
                fn=api.execute_action,
                inputs=[
                    api_project_id,
                    api_action_id,
                    api_inputs,
                    api_mode,
                    api_confirmed,
                ],
                outputs=[api_result],
                api_name="execute_action",
            )

            # execute_plan
            api_plan_project_id = gr.Textbox(label="project_id")
            api_plan_json = gr.JSON(label="plan")
            api_plan_result = gr.JSON(label="result")

            gr.Button("Execute Plan API").click(
                fn=api.execute_plan,
                inputs=[api_plan_project_id, api_plan_json, api_mode],
                outputs=[api_plan_result],
                api_name="execute_plan",
            )

            # revert_snapshot
            api_revert_project_id = gr.Textbox(label="project_id")
            api_revert_snapshot_id = gr.Textbox(label="snapshot_id")
            api_revert_result = gr.JSON(label="result")

            gr.Button("Revert Snapshot API").click(
                fn=api.revert_snapshot,
                inputs=[api_revert_project_id, api_revert_snapshot_id],
                outputs=[api_revert_result],
                api_name="revert_snapshot",
            )

            # webhook_execute
            api_wh_id = gr.Textbox(label="webhook_id")
            api_wh_payload = gr.JSON(label="payload")
            api_wh_signature = gr.Textbox(label="signature")
            api_wh_result = gr.JSON(label="result")

            gr.Button("Webhook Execute API").click(
                fn=api.webhook_execute,
                inputs=[api_wh_id, api_wh_payload, api_wh_signature],
                outputs=[api_wh_result],
                api_name="webhook_execute",
            )

            # get_registry
            api_reg_project_id = gr.Textbox(label="project_id")
            api_reg_result = gr.JSON(label="registry")

            gr.Button("Get Registry API").click(
                fn=api.get_registry,
                inputs=[api_reg_project_id],
                outputs=[api_reg_result],
                api_name="get_registry",
            )

            # get_audit_log
            api_audit_project_id = gr.Textbox(label="project_id")
            api_audit_limit = gr.Number(label="limit", value=100)
            api_audit_result = gr.JSON(label="audit_log")

            gr.Button("Get Audit Log API").click(
                fn=api.get_audit_log,
                inputs=[api_audit_project_id, api_audit_limit],
                outputs=[api_audit_result],
                api_name="get_audit_log",
            )

    return demo
