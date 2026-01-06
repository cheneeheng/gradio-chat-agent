from datetime import datetime, timezone
from typing import Any

import gradio as gr

from .chat.agent_adapter_langchain import LangChainAgentAdapter
from .chat.ux_context import build_agent_context_markdown
from .execution.engine import EngineStateStore, ExecutionEngine
from .execution.forecast import forecast_budget_exhaustion
from .execution.modes import ExecutionContext, ModePolicy
from .execution.plan import ExecutionPlan
from .execution.rollup import org_usage_rollup
from .models.state_snapshot import StateSnapshot
from .observability.export import export_session_json
from .observability.jsonl_logger import JsonlAuditLogger
from .observability.metrics import EngineMetrics
from .persistence.auth_repo import AuthRepository
from .persistence.db import make_engine, make_session_factory
from .persistence.memory_repo import MemoryRepository
from .persistence.repo import ProjectIdentity, StateRepository
from .registry.in_memory import (
    build_action_handlers,
    build_action_registry,
    build_component_registry,
)
from .replay.replay import replay_components_from_results
from .ui.diff_viz import format_state_diff_markdown
from .ui.plan_viz import format_plan_markdown_with_warnings


class GradioChatAgentApp:
    def __init__(
        self, *, db_url: str = "sqlite:///./gradio_chat_agent.sqlite3"
    ) -> None:
        self.components_registry = build_component_registry()
        self.actions_registry = build_action_registry()
        self.handlers = build_action_handlers()

        self.engine = ExecutionEngine(
            action_registry=self.actions_registry, handlers=self.handlers
        )
        self.contract_md = build_agent_context_markdown(
            components=self.components_registry, actions=self.actions_registry
        )

        self.engine_db = make_engine(db_url)
        self.session_factory = make_session_factory(self.engine_db)

        self.repo = StateRepository(self.session_factory)
        self.mem_repo = MemoryRepository(self.session_factory)
        self.auth_repo = AuthRepository(self.session_factory)

        self.repo.create_tables(self.engine_db)
        self.auth_repo.ensure_default_admin(username="admin", password="admin")

        self.agent = LangChainAgentAdapter(
            default_mode="interactive",
            components=self.components_registry,
            actions=self.actions_registry,
            repo=self.repo,
            mem_repo=self.mem_repo,
        )

        self.audit_logger = JsonlAuditLogger("./audit/audit_log.jsonl")
        self.ui: dict[str, Any] = {}

    def _initial_snapshot(self) -> StateSnapshot:
        return StateSnapshot(
            snapshot_id="snap_initial",
            timestamp=datetime.now(timezone.utc),
            components={"demo.counter": {"value": 0}},
        )

    def _user_from_request(self, request: gr.Request) -> tuple[int, str]:
        username = getattr(request, "username", None) or "anonymous"
        u = self.auth_repo.get_user(username)
        if u is None:
            raise RuntimeError(
                "Authenticated username not found in users table"
            )
        return u.user_id, u.username

    def _role_for(self, *, user_id: int, project_id: int) -> str:
        role = self.auth_repo.get_role(user_id=user_id, project_id=project_id)
        return role or "viewer"

    def _project_ident(
        self, *, user_id: int, project_id: int
    ) -> ProjectIdentity:
        return ProjectIdentity(user_id=user_id, project_id=project_id)

    def _render_counter_value(self, store: EngineStateStore) -> int:
        return int(
            store.snapshot.components.get("demo.counter", {}).get("value", 0)
        )

    def _append(
        self, history: list[tuple[str, str]], user: str, assistant: str
    ) -> list[tuple[str, str]]:
        history = list(history)
        history.append((user, assistant))
        return history

    def _format_exec_log_rows(self, results: list) -> list[list[str]]:
        rows: list[list[str]] = []
        for r in results[-30:]:
            err = f"{r.error.code}" if r.error else ""
            rows.append(
                [
                    r.timestamp.isoformat(),
                    r.action_id,
                    r.status,
                    err,
                    r.message,
                ]
            )
        return rows

    # -------------------- project boot/load --------------------

    def _load_project_state(self, ident: ProjectIdentity):
        snap = (
            self.repo.load_latest_snapshot(ident) or self._initial_snapshot()
        )
        store = EngineStateStore(snapshot=snap)
        execs = self.repo.list_recent_executions(ident, limit=200)
        return store, execs

    def on_load(self, request: gr.Request):
        user_id, username = self._user_from_request(request)
        projects = self.auth_repo.list_projects_for_user(user_id)
        if not projects:
            default_pid = self.auth_repo.ensure_project(name="default")
            self.auth_repo.ensure_membership(
                user_id=user_id, project_id=default_pid, role="admin"
            )
            projects = self.auth_repo.list_projects_for_user(user_id)

        project_id, project_name, role = projects[0]
        ident = self._project_ident(user_id=user_id, project_id=project_id)
        store, execs = self._load_project_state(ident)

        return (
            projects,  # for dropdown choices
            project_id,
            f"{username} @ {project_name} ({role})",
            store,
            execs,
            [],
            None,
            self._render_counter_value(store),
            "No state changes.",
            "",
            "",
            EngineMetrics(),
        )

    def on_project_change(self, project_id: int, request: gr.Request):
        user_id, username = self._user_from_request(request)
        role = self._role_for(user_id=user_id, project_id=project_id)

        # name for display
        projects = self.auth_repo.list_projects_for_user(user_id)
        name_by_id = {pid: name for pid, name, _ in projects}
        project_name = name_by_id.get(project_id, f"project:{project_id}")

        ident = self._project_ident(user_id=user_id, project_id=project_id)
        store, execs = self._load_project_state(ident)

        return (
            f"{username} @ {project_name} ({role})",
            store,
            execs,
            [],
            None,
            self._render_counter_value(store),
            "No state changes.",
            "",
            "",
        )

    def on_create_project(self, new_project_name: str, request: gr.Request):
        user_id, _ = self._user_from_request(request)
        pid = self.auth_repo.ensure_project(name=new_project_name.strip())
        self.auth_repo.ensure_membership(
            user_id=user_id, project_id=pid, role="admin"
        )

        projects = self.auth_repo.list_projects_for_user(user_id)
        return projects, pid

    # -------------------- chat + plan preview --------------------

    def handle_user_message(
        self,
        message: str,
        mode_value: str,
        confirmed_checkbox: bool,
        project_id: int,
        store: EngineStateStore,
        history: list[tuple[str, str]],
        exec_log: list,
        pending_plan: ExecutionPlan | None,
        metrics: EngineMetrics,
        request: gr.Request,
    ):
        user_id, username = self._user_from_request(request)
        role = self._role_for(user_id=user_id, project_id=project_id)
        user_roles = {role} | ({"admin"} if role == "admin" else set())
        ident = self._project_ident(user_id=user_id, project_id=project_id)

        if pending_plan is not None:
            history = self._append(
                history,
                message,
                "A plan is pending. Approve or reject it first.",
            )
            metrics.inc("chat.pending_plan_blocked")
            return (
                history,
                store,
                exec_log,
                pending_plan,
                self._render_counter_value(store),
                "No state changes.",
                "",
                "",
                metrics,
            )

        intent_or_plan = self.agent.message_to_intent_or_plan(
            message=message,
            state=store.snapshot.components,
            execution_mode=mode_value,
            ident=ident,
            user_roles=sorted(user_roles),
        )

        def apply_confirmation_to_intent(intent: ChatIntent) -> ChatIntent:
            if intent.type == "action_call" and confirmed_checkbox:
                return intent.model_copy(
                    update={
                        "confirmed": True,
                        "trace": {
                            **intent.trace,
                            "confirmation_source": "ui_checkbox",
                        },
                    }
                )
            return intent

        # clarification
        if (
            isinstance(intent_or_plan, ChatIntent)
            and intent_or_plan.type == "clarification_request"
        ):
            history = self._append(
                history,
                message,
                intent_or_plan.question or "Need clarification.",
            )
            metrics.inc("chat.clarifications")
            return (
                history,
                store,
                exec_log,
                None,
                self._render_counter_value(store),
                "No state changes.",
                "",
                "",
                metrics,
            )

        # plan preview in interactive mode
        if (
            isinstance(intent_or_plan, ExecutionPlan)
            and mode_value == "interactive"
        ):
            plan = intent_or_plan.model_copy(
                update={
                    "steps": [
                        apply_confirmation_to_intent(s)
                        for s in intent_or_plan.steps
                    ]
                }
            )
            history = self._append(
                history,
                message,
                f"Proposed a plan with {len(plan.steps)} steps. Review and approve.",
            )
            plan_md = format_plan_markdown_with_warnings(
                plan, actions=self.actions_registry, user_roles=user_roles
            )
            metrics.inc("plan.proposed")
            return (
                history,
                store,
                exec_log,
                plan,
                self._render_counter_value(store),
                "No state changes.",
                plan_md,
                "",
                metrics,
            )

        # execute single intent
        if isinstance(intent_or_plan, ChatIntent):
            intent = apply_confirmation_to_intent(intent_or_plan)
            ctx = ExecutionContext(
                policy=ModePolicy.for_mode(mode_value),
                user_id=username,
                user_roles=sorted(user_roles),
                project_id=str(project_id),
            )

            result = self.engine.execute_intent(
                ctx=ctx, intent=intent, store=store
            )
            self.audit_logger.log_intent_and_result(
                ident=ident, intent=intent, result=result
            )
            self.repo.save_execution_and_snapshot_atomic(
                ident=ident, result=result, snapshot=store.snapshot
            )

            exec_log = self.repo.list_recent_executions(ident, limit=200)
            diff_md = format_state_diff_markdown(result.state_diff)

            assistant_text = f"{result.status}: {result.message}"
            err_md = ""
            if result.error:
                err_md = f"### Error\n- code: `{result.error.code}`\n- detail: {result.error.detail}"
                metrics.inc(f"engine.{result.status}.{result.error.code}")
            else:
                metrics.inc("engine.success")

            history = self._append(history, message, assistant_text)
            return (
                history,
                store,
                exec_log,
                None,
                self._render_counter_value(store),
                diff_md,
                "",
                err_md,
                metrics,
            )

        # execute plan (assisted/autonomous)
        plan = intent_or_plan.model_copy(
            update={
                "steps": [
                    apply_confirmation_to_intent(s)
                    for s in intent_or_plan.steps
                ]
            }
        )
        results = self.engine.execute_plan(
            plan=plan, mode=mode_value, store=store
        )
        last = results[-1]

        for step_intent, r in zip(plan.steps, results, strict=False):
            self.audit_logger.log_intent_and_result(
                ident=ident, intent=step_intent, result=r
            )
            self.repo.save_execution_and_snapshot_atomic(
                ident=ident, result=r, snapshot=store.snapshot
            )

        exec_log = self.repo.list_recent_executions(ident, limit=200)
        diff_md = format_state_diff_markdown(last.state_diff)

        assistant_text = f"[plan:{plan.plan_id}] {last.status}: {last.message}"
        err_md = ""
        if last.error:
            err_md = f"### Error\n- code: `{last.error.code}`\n- detail: {last.error.detail}"
            metrics.inc(f"engine.{last.status}.{last.error.code}")
        else:
            metrics.inc("engine.plan.success")

        history = self._append(history, message, assistant_text)
        return (
            history,
            store,
            exec_log,
            None,
            self._render_counter_value(store),
            diff_md,
            "",
            err_md,
            metrics,
        )

    def handle_approve_plan(
        self,
        mode_value: str,
        confirmed_checkbox: bool,
        project_id: int,
        store: EngineStateStore,
        history: list[tuple[str, str]],
        exec_log: list,
        pending_plan: ExecutionPlan | None,
        metrics: EngineMetrics,
        request: gr.Request,
    ):
        user_id, username = self._user_from_request(request)
        role = self._role_for(user_id=user_id, project_id=project_id)
        user_roles = {role} | ({"admin"} if role == "admin" else set())
        ident = self._project_ident(user_id=user_id, project_id=project_id)

        if pending_plan is None:
            history = self._append(
                history, "(system)", "No pending plan to approve."
            )
            metrics.inc("plan.approve.no_plan")
            return (
                history,
                store,
                exec_log,
                None,
                self._render_counter_value(store),
                "No state changes.",
                "",
                "",
                metrics,
            )

        if role == "viewer":
            history = self._append(
                history, "(system)", "You are a viewer; cannot execute a plan."
            )
            metrics.inc("auth.viewer_blocked")
            return (
                history,
                store,
                exec_log,
                pending_plan,
                self._render_counter_value(store),
                "No state changes.",
                "",
                "",
                metrics,
            )

        plan = pending_plan
        if confirmed_checkbox:
            plan = plan.model_copy(
                update={
                    "steps": [
                        s.model_copy(update={"confirmed": True})
                        for s in plan.steps
                    ]
                }
            )

        results = self.engine.execute_plan(
            plan=plan, mode=mode_value, store=store
        )
        last = results[-1]

        for step_intent, r in zip(plan.steps, results, strict=False):
            self.audit_logger.log_intent_and_result(
                ident=ident, intent=step_intent, result=r
            )
            self.repo.save_execution_and_snapshot_atomic(
                ident=ident, result=r, snapshot=store.snapshot
            )

        exec_log = self.repo.list_recent_executions(ident, limit=200)

        history = self._append(
            history,
            "(system)",
            f"Executed plan `{plan.plan_id}` with {len(results)} results.",
        )
        diff_md = format_state_diff_markdown(last.state_diff)
        metrics.inc("plan.executed")

        err_md = ""
        if last.error:
            err_md = f"### Error\n- code: `{last.error.code}`\n- detail: {last.error.detail}"
            metrics.inc(f"engine.{last.status}.{last.error.code}")

        return (
            history,
            store,
            exec_log,
            None,
            self._render_counter_value(store),
            diff_md,
            "",
            err_md,
            metrics,
        )

    def handle_reject_plan(
        self,
        history: list[tuple[str, str]],
        pending_plan: ExecutionPlan | None,
        metrics: EngineMetrics,
    ):
        if pending_plan is None:
            history = self._append(
                history, "(system)", "No pending plan to reject."
            )
            metrics.inc("plan.reject.no_plan")
            return history, None, "", metrics
        history = self._append(
            history,
            "(system)",
            f"Rejected plan `{pending_plan.plan_id}`. Please clarify what you want.",
        )
        metrics.inc("plan.rejected")
        return history, None, "", metrics

    def handle_replay(
        self,
        project_id: int,
        store: EngineStateStore,
        metrics: EngineMetrics,
        request: gr.Request,
    ):
        user_id, _ = self._user_from_request(request)
        ident = self._project_ident(user_id=user_id, project_id=project_id)

        results = self.repo.list_recent_executions(ident, limit=5000)
        rebuilt = replay_components_from_results(
            initial_components=self._initial_snapshot().components,
            results=results,
        )

        store.snapshot = StateSnapshot(
            snapshot_id=f"replay_{datetime.now(timezone.utc).isoformat()}",
            timestamp=datetime.now(timezone.utc),
            components=rebuilt,
        )
        metrics.inc("replay.executed")
        return store, self._render_counter_value(store), metrics

    def handle_export_session(self, project_id: int, request: gr.Request):
        user_id, _ = self._user_from_request(request)
        ident = self._project_ident(user_id=user_id, project_id=project_id)
        return export_session_json(self.repo, self.mem_repo, ident)

    def load_project_members(self, project_id: int, request: gr.Request):
        user_id, _ = self._user_from_request(request)
        role = self._role_for(user_id=user_id, project_id=project_id)
        if role != "admin":
            return []

        members = self.auth_repo.list_members(project_id)
        return [[m.username, m.role] for m in members]

    def update_project_member(
        self, project_id: int, username: str, role: str, request: gr.Request
    ):
        if username == request.username and role != "admin":
            raise ValueError("You cannot remove your own admin role")

        user_id, _ = self._user_from_request(request)
        if self._role_for(user_id=user_id, project_id=project_id) != "admin":
            raise PermissionError("Only admins can modify roles")

        user = self.auth_repo.get_user(username)
        if not user:
            raise ValueError("User not found")

        self.auth_repo.ensure_membership(
            user_id=user.user_id,
            project_id=project_id,
            role=role,
        )
        return self.load_project_members(project_id, request)

    def api_execute_action(
        self,
        project_id: int,
        action_id: str,
        inputs: dict,
        mode: str,
        confirmed: bool,
        request: gr.Request,
    ):
        user_id, username = self._user_from_request(request)
        role = self._role_for(user_id=user_id, project_id=project_id)

        ident = self._project_ident(user_id=user_id, project_id=project_id)

        ctx = ExecutionContext(
            policy=ModePolicy.for_mode(mode),
            user_id=username,
            user_roles=[role],
            project_id=str(project_id),
        )

        store, _ = self._load_project_state(ident)

        intent = ChatIntent(
            type="action_call",
            request_id=f"api:{action_id}",
            timestamp=datetime.now(timezone.utc),
            execution_mode=mode,
            action_id=action_id,
            inputs=inputs,
            confirmed=confirmed,
            trace={"source": "api"},
        )

        result = self.engine.execute_intent(
            ctx=ctx, intent=intent, store=store
        )

        self.repo.save_execution_and_snapshot_atomic(
            ident=ident,
            result=result,
            snapshot=store.snapshot,
        )

        return result.model_dump()

    def api_get_audit_log(
        self,
        project_id: int,
        limit: int,
        request: gr.Request,
    ):
        user_id, _ = self._user_from_request(request)
        role = self._role_for(user_id=user_id, project_id=project_id)

        if role not in {"viewer", "operator", "admin"}:
            raise PermissionError("Not authorized")

        ident = ProjectIdentity(user_id=user_id, project_id=project_id)
        execs = self.repo.list_recent_executions(ident, limit=limit)

        return [e.model_dump() for e in execs]

    def api_webhook_execute(
        self,
        webhook_id: int,
        payload: dict,
    ):
        webhook = self.repo.get_webhook(webhook_id)
        if not verify_signature(payload, webhook.secret):
            raise PermissionError("Invalid signature")

        inputs = render_template(webhook.inputs_template, payload)

        return self.api_execute_action(
            project_id=webhook.project_id,
            action_id=webhook.action_id,
            inputs=inputs,
            mode="assisted",
            confirmed=True,
        )

    def api_budget_forecast(self, project_id: int, request: gr.Request):
        user_id, _ = self._user_from_request(request)
        role = self._role_for(user_id=user_id, project_id=project_id)

        if role not in {"operator", "admin"}:
            raise PermissionError("Not authorized")

        limits = self.repo.get_project_limits(project_id)
        if not limits or limits.daily_budget is None:
            return {"status": "no_budget"}

        return forecast_budget_exhaustion(
            self.repo,
            project_id,
            limits.daily_budget,
        )

    def api_org_rollup(self, request: gr.Request):
        user_id, _ = self._user_from_request(request)
        return org_usage_rollup(self.repo, user_id)

    def update_project_limits(
        self, project_id, minute, hour, day, budget, request
    ):
        user_id, _ = self._user_from_request(request)
        if self._role_for(user_id=user_id, project_id=project_id) != "admin":
            raise PermissionError("Admin only")

        self.repo.set_project_limits(
            project_id=project_id,
            max_actions_per_minute=minute,
            max_actions_per_hour=hour,
            max_actions_per_day=day,
            daily_budget=budget,
        )

    # -------------------- layout and binding --------------------

    def build_layout(self) -> gr.Blocks:
        with gr.Blocks(title="gradio-chat-agent") as demo:
            with gr.Accordion("Project members (admin only)", open=False):
                self.ui["member_table"] = gr.Dataframe(
                    headers=["username", "role"],
                    datatype=["str", "str"],
                    row_count=5,
                    col_count=(2, "fixed"),
                )
                self.ui["member_username"] = gr.Textbox(label="Username")
                self.ui["member_role"] = gr.Dropdown(
                    choices=["viewer", "operator", "admin"],
                    label="Role",
                )
                self.ui["update_member_btn"] = gr.Button("Update role")

            with gr.Accordion("Project limits (admin)", open=False):
                self.ui["limit_minute"] = gr.Number(
                    label="Max actions / minute"
                )
                self.ui["limit_hour"] = gr.Number(label="Max actions / hour")
                self.ui["limit_day"] = gr.Number(label="Max actions / day")
                self.ui["limit_budget"] = gr.Number(label="Daily budget")
                self.ui["save_limits_btn"] = gr.Button("Save limits")

            with gr.Row():
                self.ui["project_dropdown"] = gr.Dropdown(
                    choices=[], label="Project", value=None
                )
                self.ui["create_project_name"] = gr.Textbox(
                    label="New project name", value=""
                )
                self.ui["create_project_btn"] = gr.Button(
                    "Create / join as admin"
                )
                self.ui["identity_view"] = gr.Markdown(value="")

            self.ui["mode"] = gr.Dropdown(
                choices=["interactive", "assisted", "autonomous"],
                value="interactive",
                label="Execution mode",
            )
            self.ui["confirm"] = gr.Checkbox(
                label="Confirm (for gated actions)", value=False
            )

            with gr.Row():
                with gr.Column(scale=2):
                    self.ui["chatbot"] = gr.Chatbot(label="Chat", height=420)
                    self.ui["user_msg"] = gr.Textbox(
                        label="Message", placeholder="Type a request..."
                    )

                    with gr.Row():
                        self.ui["approve_plan_btn"] = gr.Button(
                            "Approve plan", variant="primary"
                        )
                        self.ui["reject_plan_btn"] = gr.Button(
                            "Reject plan", variant="secondary"
                        )
                        self.ui["replay_btn"] = gr.Button(
                            "Replay from log", variant="secondary"
                        )
                        self.ui["export_btn"] = gr.Button(
                            "Export session JSON", variant="secondary"
                        )

                    self.ui["plan_preview"] = gr.Markdown(value="")
                    self.ui["export_json"] = gr.Textbox(
                        label="Exported session JSON", value="", lines=8
                    )

                with gr.Column(scale=1):
                    self.ui["counter_view"] = gr.Number(
                        label="Counter value", value=0, precision=0
                    )
                    with gr.Accordion("State changes", open=True):
                        self.ui["diff_view"] = gr.Markdown(
                            value="No state changes."
                        )
                    with gr.Accordion("Last error", open=True):
                        self.ui["error_view"] = gr.Markdown(value="")
                    with gr.Accordion("Metrics", open=True):
                        self.ui["metrics_view"] = gr.Markdown(
                            value="No metrics yet."
                        )
                    with gr.Accordion("Execution log", open=True):
                        self.ui["exec_table"] = gr.Dataframe(
                            headers=[
                                "timestamp",
                                "action_id",
                                "status",
                                "error",
                                "message",
                            ],
                            datatype=["str", "str", "str", "str", "str"],
                            row_count=10,
                            col_count=(5, "fixed"),
                        )
                    with gr.Accordion("Agent-visible contracts", open=False):
                        gr.Markdown(value=self.contract_md)

            self.ui["api_execute"] = gr.JSON(visible=False)

            self.ui["project_id_state"] = gr.State(None)
            self.ui["store_state"] = gr.State(
                EngineStateStore(snapshot=self._initial_snapshot())
            )
            self.ui["history_state"] = gr.State([])
            self.ui["pending_plan_state"] = gr.State(None)
            self.ui["exec_log_state"] = gr.State([])
            self.ui["metrics_state"] = gr.State(EngineMetrics())
            self.ui["demo"] = demo

        return demo

    def bind_events(self) -> None:
        demo: gr.Blocks = self.ui["demo"]

        project_dropdown: gr.Dropdown = self.ui["project_dropdown"]
        create_project_name: gr.Textbox = self.ui["create_project_name"]
        create_project_btn: gr.Button = self.ui["create_project_btn"]
        identity_view: gr.Markdown = self.ui["identity_view"]

        mode = self.ui["mode"]
        confirm = self.ui["confirm"]

        chatbot = self.ui["chatbot"]
        user_msg = self.ui["user_msg"]

        counter_view = self.ui["counter_view"]
        diff_view = self.ui["diff_view"]
        error_view = self.ui["error_view"]
        exec_table = self.ui["exec_table"]
        plan_preview = self.ui["plan_preview"]
        metrics_view = self.ui["metrics_view"]
        export_json = self.ui["export_json"]

        approve_btn = self.ui["approve_plan_btn"]
        reject_btn = self.ui["reject_plan_btn"]
        replay_btn = self.ui["replay_btn"]
        export_btn = self.ui["export_btn"]

        project_id_state = self.ui["project_id_state"]
        store_state = self.ui["store_state"]
        history_state = self.ui["history_state"]
        pending_plan_state = self.ui["pending_plan_state"]
        exec_log_state = self.ui["exec_log_state"]
        metrics_state = self.ui["metrics_state"]

        update_member_btn = self.ui["update_member_btn"]
        member_username = self.ui["member_username"]
        member_role = self.ui["member_role"]
        member_table = self.ui["member_table"]

        # initial load: populate project dropdown choices + select first project
        demo.load(
            fn=self.on_load,
            inputs=[],
            outputs=[
                project_dropdown,
                project_id_state,
                identity_view,
                store_state,
                exec_log_state,
                history_state,
                pending_plan_state,
                counter_view,
                diff_view,
                plan_preview,
                error_view,
                metrics_state,
            ],
        ).then(
            fn=lambda execs: self._format_exec_log_rows(execs),
            inputs=[exec_log_state],
            outputs=[exec_table],
        ).then(
            fn=lambda m: m.render_markdown(),
            inputs=[metrics_state],
            outputs=[metrics_view],
        ).then(
            fn=lambda pid: gr.update(value=pid),
            inputs=[project_id_state],
            outputs=[project_dropdown],
        )

        # change project
        project_dropdown.change(
            fn=self.on_project_change,
            inputs=[project_dropdown],
            outputs=[
                identity_view,
                store_state,
                exec_log_state,
                history_state,
                pending_plan_state,
                counter_view,
                diff_view,
                plan_preview,
                error_view,
            ],
        ).then(
            fn=lambda execs: self._format_exec_log_rows(execs),
            inputs=[exec_log_state],
            outputs=[exec_table],
        )

        # create project then select it
        create_project_btn.click(
            fn=self.on_create_project,
            inputs=[create_project_name],
            outputs=[project_dropdown, project_id_state],
        ).then(
            fn=lambda pid: gr.update(value=pid),
            inputs=[project_id_state],
            outputs=[project_dropdown],
        )

        # chat submit
        user_msg.submit(
            fn=self.handle_user_message,
            inputs=[
                user_msg,
                mode,
                confirm,
                project_dropdown,
                store_state,
                history_state,
                exec_log_state,
                pending_plan_state,
                metrics_state,
            ],
            outputs=[
                chatbot,
                store_state,
                exec_log_state,
                pending_plan_state,
                counter_view,
                diff_view,
                plan_preview,
                error_view,
                metrics_state,
            ],
        ).then(lambda: "", None, user_msg).then(
            fn=lambda execs: self._format_exec_log_rows(execs),
            inputs=[exec_log_state],
            outputs=[exec_table],
        ).then(
            fn=lambda m: m.render_markdown(),
            inputs=[metrics_state],
            outputs=[metrics_view],
        )

        approve_btn.click(
            fn=self.handle_approve_plan,
            inputs=[
                mode,
                confirm,
                project_dropdown,
                store_state,
                history_state,
                exec_log_state,
                pending_plan_state,
                metrics_state,
            ],
            outputs=[
                chatbot,
                store_state,
                exec_log_state,
                pending_plan_state,
                counter_view,
                diff_view,
                plan_preview,
                error_view,
                metrics_state,
            ],
        ).then(
            fn=lambda execs: self._format_exec_log_rows(execs),
            inputs=[exec_log_state],
            outputs=[exec_table],
        ).then(
            fn=lambda m: m.render_markdown(),
            inputs=[metrics_state],
            outputs=[metrics_view],
        )

        reject_btn.click(
            fn=self.handle_reject_plan,
            inputs=[history_state, pending_plan_state, metrics_state],
            outputs=[chatbot, pending_plan_state, plan_preview, metrics_state],
        ).then(
            fn=lambda m: m.render_markdown(),
            inputs=[metrics_state],
            outputs=[metrics_view],
        )

        replay_btn.click(
            fn=self.handle_replay,
            inputs=[project_dropdown, store_state, metrics_state],
            outputs=[store_state, counter_view, metrics_state],
        ).then(
            fn=lambda m: m.render_markdown(),
            inputs=[metrics_state],
            outputs=[metrics_view],
        )

        export_btn.click(
            fn=self.handle_export_session,
            inputs=[project_dropdown],
            outputs=[export_json],
        )

        project_dropdown.change(
            fn=self.load_project_members,
            inputs=[project_dropdown],
            outputs=[member_table],
        )

        update_member_btn.click(
            fn=self.update_project_member,
            inputs=[project_dropdown, member_username, member_role],
            outputs=[member_table],
        )

        demo.api(
            fn=self.api_execute_action,
            inputs=[
                gr.Number(label="project_id"),
                gr.Textbox(label="action_id"),
                gr.JSON(label="inputs"),
                gr.Dropdown(
                    choices=["interactive", "assisted", "autonomous"],
                    value="assisted",
                ),
                gr.Checkbox(label="confirmed", value=False),
            ],
            outputs=gr.JSON(),
        )
        demo.api(
            fn=self.api_get_audit_log,
            inputs=[gr.Number(), gr.Number(value=100)],
            outputs=gr.JSON(),
        )
        demo.api(
            fn=self.api_budget_forecast,
            inputs=[gr.Number(label="project_id")],
            outputs=gr.JSON(),
        )
        demo.api(
            fn=self.api_org_rollup,
            inputs=[],
            outputs=gr.JSON(),
        )

    def launch(self) -> None:
        demo = self.build_layout()
        self.bind_events()

        def auth_func(username: str, password: str) -> bool:
            return self.auth_repo.verify_login(username, password)

        demo.launch(auth=auth_func)


def main() -> None:
    GradioChatAgentApp().launch()


if __name__ == "__main__":
    main()
