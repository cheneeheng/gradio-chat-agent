"""UI layout and event handling for the Gradio Chat Agent.

This module defines the structural components of the Gradio interface and the
logic for handling user interactions, agent communication, and engine
execution.
"""

import gradio as gr

from gradio_chat_agent.api.endpoints import ApiEndpoints
from gradio_chat_agent.chat.adapter import AgentAdapter
from gradio_chat_agent.execution.engine import ExecutionEngine
from gradio_chat_agent.models.enums import (
    ExecutionMode,
    ExecutionStatus,
    IntentType,
)
from gradio_chat_agent.models.intent import ChatIntent
from gradio_chat_agent.models.plan import ExecutionPlan
from gradio_chat_agent.ui.theme import AgentTheme
from gradio_chat_agent.utils import encode_media


DEFAULT_PROJECT_ID = "default_project"
DEFAULT_USER_ID = "admin_user"

STATUS_SUCCESS_HTML = '<div style="color: green; font-size: 1.2rem;">✅ Success</div>'
STATUS_PENDING_HTML = '<div style="color: orange; font-size: 1.2rem;">⏳ Pending Approval</div>'
STATUS_FAILED_HTML = '<div style="color: red; font-size: 1.2rem;">❌ Failed/Rejected</div>'
STATUS_READY_HTML = '<div style="color: gray; font-size: 1.2rem;">🟢 Ready</div>'

CUSTOM_CSS = """
/* Enhance Chatbot Bubbles */
.message.user {
    border-top-right-radius: 0 !important;
}
.message.bot {
    border-top-left-radius: 0 !important;
}

/* Plan Preview Card */
.plan-preview {
    border: 1px solid var(--primary-200) !important;
    background: var(--primary-50) !important;
    padding: 1rem !important;
    border-radius: var(--radius-lg) !important;
    margin-top: 1rem !important;
}

/* State JSON viewers */
.json-viewer {
    font-family: var(--font-mono) !important;
    font-size: 0.85rem !important;
}
"""


class UIController:
    """Controller for handling UI events and interacting with the engine."""

    def __init__(self, engine: ExecutionEngine, adapter: AgentAdapter):
        self.engine = engine
        self.adapter = adapter

    def fetch_state(self, pid: str) -> dict:
        """Fetch latest state components for a project."""
        snapshot = self.engine.repository.get_latest_snapshot(pid)
        if snapshot:
            return snapshot.components
        return {}

    def fetch_facts_df(self, pid: str, uid: str) -> list:
        """Fetch session facts as a list of lists for Dataframe."""
        facts = self.engine.repository.get_session_facts(pid, uid)
        return [[k, str(v)] for k, v in facts.items()]

    def fetch_members_df(self, pid: str) -> list:
        """Fetch project members as a list of lists for Dataframe."""
        members = self.engine.repository.get_project_members(pid)
        return [[m["user_id"], m["role"]] for m in members]

    def refresh_ui(self, pid: str, uid: str):
        """Refresh all UI components."""
        state = self.fetch_state(pid)
        reg_info = {
            "components": [
                c.component_id for c in self.engine.registry.list_components()
            ],
            "actions": [
                a.action_id for a in self.engine.registry.list_actions()
            ],
        }
        facts_data = self.fetch_facts_df(pid, uid)
        members_data = self.fetch_members_df(pid)
        return (
            state,
            {},
            reg_info,
            facts_data,
            members_data,
            {}, # last_intent
            {}, # last_result
            STATUS_READY_HTML,
        )

    def on_add_fact(self, pid: str, uid: str, key: str, val: str):
        """Handler for adding a session fact."""
        if key:
            self.engine.repository.save_session_fact(pid, uid, key, val)
        return self.fetch_facts_df(pid, uid), "", ""

    def on_delete_fact(self, pid: str, uid: str, key: str):
        """Handler for deleting a session fact."""
        if key:
            self.engine.repository.delete_session_fact(pid, uid, key)
        return self.fetch_facts_df(pid, uid), ""

    def on_add_member(self, pid: str, uid: str, target_uid: str, role: str):
        """Handler for adding a project member."""
        if target_uid and role:
            self.engine.repository.add_project_member(pid, target_uid, role)
        return self.fetch_members_df(pid), "", "viewer"

    def on_remove_member(self, pid: str, uid: str, target_uid: str):
        """Handler for removing a project member."""
        if target_uid:
            self.engine.repository.remove_project_member(pid, target_uid)
        return self.fetch_members_df(pid), ""

    def on_submit(self, message_data, history, pid, uid, mode):
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
        snapshot = self.engine.repository.get_latest_snapshot(pid)
        if not snapshot:
            from gradio_chat_agent.models.state_snapshot import StateSnapshot

            snapshot = StateSnapshot(snapshot_id="init", components={})

        state_dict = snapshot.components
        facts = self.engine.repository.get_session_facts(pid, uid)

        comp_reg = {
            c.component_id: c.model_dump()
            for c in self.engine.registry.list_components()
        }
        act_reg = {
            a.action_id: a.model_dump()
            for a in self.engine.registry.list_actions()
        }

        # Visibility Filtering
        # 1. Determine user role for this project
        members = self.engine.repository.get_project_members(pid)
        user_role = "viewer"  # Default
        for m in members:
            if m["user_id"] == uid:
                user_role = m["role"]
                break

        # 2. Filter actions
        # 'developer' visibility actions are only shown to 'admin'
        if user_role != "admin":
            act_reg = {
                aid: adef
                for aid, adef in act_reg.items()
                if adef["permission"]["visibility"] != "developer"
            }

        # Media processing
        media = None
        if files:
            file_path = files[0]
            media = encode_media(file_path)
            media["type"] = "image"

        try:
            result = self.adapter.message_to_intent_or_plan(
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
            return (
                "",
                new_history,
                state_dict,
                {"error": str(e)},
                gr.update(),
                gr.update(visible=False),
                None,
                {}, # last_intent
                {}, # last_result
                STATUS_FAILED_HTML,
            )

        # 4. Handle Result
        last_intent_json = result.model_dump(mode="json") if result else {}
        if isinstance(result, ExecutionPlan):
            plan_md = f"## Proposed Plan (ID: {result.plan_id})\n"
            for i, step in enumerate(result.steps):
                plan_md += f"{i + 1}. **{step.action_id}**: `{step.inputs}`\n"

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
                last_intent_json,
                {}, # last_result
                STATUS_PENDING_HTML,
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
                    last_intent_json,
                    {}, # last_result
                    STATUS_READY_HTML,
                )

            elif intent.type == IntentType.ACTION_CALL:
                exec_result = self.engine.execute_intent(
                    pid, intent, user_roles=[user_role], user_id=uid
                )
                last_result_json = exec_result.model_dump(mode="json")

                if exec_result.status == "success":
                    resp = f"Executed `{intent.action_id}`.\n\nResult: {exec_result.message}"
                    new_history.append({"role": "assistant", "content": resp})

                    new_snapshot = self.engine.repository.get_latest_snapshot(
                        pid
                    )
                    new_state = new_snapshot.components if new_snapshot else {}

                    return (
                        "",
                        new_history,
                        new_state,
                        exec_result.state_diff,
                        "No plan pending.",
                        gr.update(visible=False),
                        None,
                        last_intent_json,
                        last_result_json,
                        STATUS_SUCCESS_HTML,
                    )

                elif (
                    exec_result.error
                    and exec_result.error.code == "confirmation_required"
                ):
                    resp = f"Action `{intent.action_id}` requires confirmation. Please type 'confirm' to proceed."
                    new_history.append({"role": "assistant", "content": resp})
                    return (
                        "",
                        new_history,
                        state_dict,
                        {},
                        "No plan pending.",
                        gr.update(visible=False),
                        None,
                        last_intent_json,
                        last_result_json,
                        STATUS_PENDING_HTML,
                    )

                elif exec_result.status == ExecutionStatus.PENDING_APPROVAL:
                    resp = f"Action `{intent.action_id}` is **pending approval**. {exec_result.message}"
                    new_history.append({"role": "assistant", "content": resp})
                    return (
                        "",
                        new_history,
                        state_dict,
                        {},
                        "No plan pending.",
                        gr.update(visible=False),
                        None,
                        last_intent_json,
                        last_result_json,
                        STATUS_PENDING_HTML,
                    )

                else:
                    resp = f"Action Failed/Rejected: {exec_result.message}"
                    new_history.append({"role": "assistant", "content": resp})
                    return (
                        "",
                        new_history,
                        state_dict,
                        {},
                        "No plan pending.",
                        gr.update(visible=False),
                        None,
                        last_intent_json,
                        last_result_json,
                        STATUS_FAILED_HTML,
                    )

        return (
            "",
            new_history,
            state_dict,
            {},
            "No plan pending.",
            gr.update(visible=False),
            None,
            {}, # last_intent
            {}, # last_result
            STATUS_READY_HTML,
        )

    def on_approve_plan(self, plan, history, pid, uid):
        """Handler for approving a pending plan."""
        if not plan:
            return (
                history,
                {},
                {},
                "No plan",
                gr.update(visible=False),
                None,
                {},  # last_intent
                {},  # last_result
                STATUS_READY_HTML,
            )

        # Determine user role
        members = self.engine.repository.get_project_members(pid)
        user_role = "viewer"
        for m in members:
            if m["user_id"] == uid:
                user_role = m["role"]
                break

        results = self.engine.execute_plan(
            pid, plan, user_roles=[user_role], user_id=uid
        )

        summary = "### Plan Execution Result\n"
        final_diff = []
        for res in results:
            status_icon = "✅" if res.status == "success" else "❌"
            summary += f"- {status_icon} **{res.action_id}**: {res.message}\n"
            if res.state_diff:
                final_diff.extend(res.state_diff)

        history.append({"role": "assistant", "content": summary})

        snapshot = self.engine.repository.get_latest_snapshot(pid)
        new_state = snapshot.components if snapshot else {}

        last_intent_json = plan.model_dump(mode="json")
        last_result_json = [res.model_dump(mode="json") for res in results]

        return (
            history,
            new_state,
            final_diff,
            "Plan Executed.",
            gr.update(visible=False),
            None,
            last_intent_json,
            last_result_json,
            STATUS_SUCCESS_HTML,
        )

    def on_reject_plan(self, history):
        """Handler for rejecting a pending plan."""
        history.append({"role": "assistant", "content": "Plan rejected."})
        return (
            history,
            {},  # state_json (no change)
            {},  # diff_json (no change)
            "Plan rejected.",  # plan_display
            gr.update(visible=False),  # plan_group
            None,  # pending_plan_state
            {},  # last_intent
            {},  # last_result
            STATUS_READY_HTML,
        )


def create_ui(engine: ExecutionEngine, adapter: AgentAdapter) -> gr.Blocks:
    """Constructs the Gradio UI and sets up event handlers.

    Args:
        engine: The authoritative execution engine for state mutations.
        adapter: The chat agent adapter for natural language interpretation.

    Returns:
        A Gradio gr.Blocks object containing the application layout.
    """
    api = ApiEndpoints(engine)
    controller = UIController(engine, adapter)
    theme = AgentTheme()

    with gr.Blocks(
        title="Gradio Chat Agent", theme=theme, css=CUSTOM_CSS
    ) as demo:
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

                status_indicator = gr.HTML(STATUS_READY_HTML, label="System Status")

                reset_btn = gr.Button(
                    "Reset State (Debug)", variant="secondary"
                )

            # --- Main Chat Area ---
            with gr.Column(scale=2):
                chatbot = gr.Chatbot(label="Agent", height=600)
                msg_input = gr.MultimodalTextbox(
                    placeholder="Type a command or upload image...",
                    label="Command",
                    lines=2,
                )
                submit_btn = gr.Button("Submit", variant="primary")

                # Plan Preview (Hidden by default)
                with gr.Group(
                    visible=False, elem_classes="plan-preview"
                ) as plan_group:
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
                        state_json = gr.JSON(
                            label="Current State", elem_classes="json-viewer"
                        )
                    with gr.Tab("Diffs"):
                        diff_json = gr.JSON(
                            label="Last Action Diff",
                            elem_classes="json-viewer",
                        )
                    with gr.Tab("Trace"):
                        with gr.Tabs():
                            with gr.Tab("Last Intent"):
                                intent_json = gr.JSON(
                                    label="Last Intent",
                                    elem_classes="json-viewer",
                                )
                            with gr.Tab("Last Result"):
                                result_json = gr.JSON(
                                    label="Last Execution Result",
                                    elem_classes="json-viewer",
                                )
                    with gr.Tab("Registry"):
                        registry_json = gr.JSON(
                            label="Available Actions",
                            elem_classes="json-viewer",
                        )
                    with gr.Tab("Memory"):
                        memory_df = gr.Dataframe(
                            headers=["Key", "Value"],
                            label="Session Facts",
                            interactive=False,
                            wrap=True,
                        )
                        with gr.Accordion("Manage Facts", open=False):
                            with gr.Row():
                                mem_key_input = gr.Textbox(label="Key")
                                mem_val_input = gr.Textbox(label="Value")
                            add_fact_btn = gr.Button(
                                "Add/Update Fact", size="sm"
                            )

                            with gr.Row():
                                del_key_input = gr.Textbox(
                                    label="Key to Delete"
                                )
                                del_fact_btn = gr.Button(
                                    "Delete Fact", size="sm", variant="stop"
                                )

                            refresh_mem_btn = gr.Button(
                                "Refresh Memory",
                                size="sm",
                                variant="secondary",
                            )

                    with gr.Tab("Team"):
                        team_df = gr.Dataframe(
                            headers=["User ID", "Role"],
                            label="Project Members",
                            interactive=False,
                            wrap=True,
                        )
                        with gr.Accordion("Manage Members", open=False):
                            with gr.Row():
                                team_user_input = gr.Textbox(label="User ID")
                                team_role_input = gr.Dropdown(
                                    choices=["viewer", "operator", "admin"],
                                    label="Role",
                                    value="viewer",
                                )
                            with gr.Row():
                                add_member_btn = gr.Button(
                                    "Add/Update Member", size="sm"
                                )
                                remove_member_btn = gr.Button(
                                    "Remove Member", size="sm", variant="stop"
                                )

                            refresh_team_btn = gr.Button(
                                "Refresh Team", size="sm", variant="secondary"
                            )

        # --- Event Bindings ---

        # Initial Load
        demo.load(
            controller.refresh_ui,
            inputs=[project_id_state, user_id_state],
            outputs=[
                state_json,
                diff_json,
                registry_json,
                memory_df,
                team_df,
                intent_json,
                result_json,
                status_indicator,
            ],
        )

        # Chat
        submit_btn.click(
            controller.on_submit,
            inputs=[
                msg_input,
                chatbot,
                project_id_state,
                user_id_state,
                execution_mode,
            ],
            outputs=[
                msg_input,
                chatbot,
                state_json,
                diff_json,
                plan_display,
                plan_group,
                pending_plan_state,
                intent_json,
                result_json,
                status_indicator,
            ],
        )
        msg_input.submit(
            controller.on_submit,
            inputs=[
                msg_input,
                chatbot,
                project_id_state,
                user_id_state,
                execution_mode,
            ],
            outputs=[
                msg_input,
                chatbot,
                state_json,
                diff_json,
                plan_display,
                plan_group,
                pending_plan_state,
                intent_json,
                result_json,
                status_indicator,
            ],
        )

        # Plan Approval
        approve_plan_btn.click(
            controller.on_approve_plan,
            inputs=[
                pending_plan_state,
                chatbot,
                project_id_state,
                user_id_state,
            ],
            outputs=[
                chatbot,
                state_json,
                diff_json,
                plan_display,
                plan_group,
                pending_plan_state,
                intent_json,
                result_json,
                status_indicator,
            ],
        )

        # Memory Handlers
        add_fact_btn.click(
            controller.on_add_fact,
            inputs=[
                project_id_state,
                user_id_state,
                mem_key_input,
                mem_val_input,
            ],
            outputs=[memory_df, mem_key_input, mem_val_input],
        )
        del_fact_btn.click(
            controller.on_delete_fact,
            inputs=[project_id_state, user_id_state, del_key_input],
            outputs=[memory_df, del_key_input],
        )
        refresh_mem_btn.click(
            controller.fetch_facts_df,
            inputs=[project_id_state, user_id_state],
            outputs=[memory_df],
        )

        # Team Handlers
        add_member_btn.click(
            controller.on_add_member,
            inputs=[
                project_id_state,
                user_id_state,
                team_user_input,
                team_role_input,
            ],
            outputs=[team_df, team_user_input, team_role_input],
        )
        remove_member_btn.click(
            controller.on_remove_member,
            inputs=[project_id_state, user_id_state, team_user_input],
            outputs=[team_df, team_user_input],
        )
        refresh_team_btn.click(
            controller.fetch_members_df,
            inputs=[project_id_state],
            outputs=[team_df],
        )

        # API Endpoints (Keeping existing connections)
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

            # simulate_action
            api_sim_project_id = gr.Textbox(label="project_id")
            api_sim_action_id = gr.Textbox(label="action_id")
            api_sim_inputs = gr.JSON(label="inputs")
            api_sim_mode = gr.Textbox(label="mode")
            api_sim_result = gr.JSON(label="result")

            gr.Button("Simulate API").click(
                fn=api.simulate_action,
                inputs=[
                    api_sim_project_id,
                    api_sim_action_id,
                    api_sim_inputs,
                    api_sim_mode,
                ],
                outputs=[api_sim_result],
                api_name="simulate_action",
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

            # simulate_plan
            api_sim_plan_project_id = gr.Textbox(label="project_id")
            api_sim_plan_json = gr.JSON(label="plan")
            api_sim_plan_result = gr.JSON(label="result")

            gr.Button("Simulate Plan API").click(
                fn=api.simulate_plan,
                inputs=[api_sim_plan_project_id, api_sim_plan_json, api_mode],
                outputs=[api_sim_plan_result],
                api_name="simulate_plan",
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
                inputs=[api_reg_project_id, user_id_state],
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

    return demo
