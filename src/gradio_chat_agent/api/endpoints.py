"""API Endpoints implementation for the Gradio Chat Agent.

This module defines the logic for the headless API endpoints exposed via Gradio.
"""

import uuid
from typing import Any

from gradio_chat_agent.execution.engine import ExecutionEngine
from gradio_chat_agent.models.enums import (
    ExecutionMode,
    IntentType,
    MembershipOp,
    ProjectOp,
    ScheduleOp,
    WebhookOp,
)
from gradio_chat_agent.models.intent import ChatIntent
from gradio_chat_agent.models.plan import ExecutionPlan


class ApiEndpoints:
    """Handlers for API endpoints."""

    def __init__(self, engine: ExecutionEngine):
        """Initialize with the execution engine."""
        self.engine = engine

    def execute_action(
        self,
        project_id: str,
        action_id: str,
        inputs: dict[str, Any],
        mode: str = "assisted",
        confirmed: bool = False,
    ) -> dict[str, Any]:
        """Executes a single action via the engine.

        Args:
            project_id: The target project ID.
            action_id: The identifier of the action to execute.
            inputs: A dictionary of arguments matching the action's input schema.
            mode: Execution mode (interactive, assisted, autonomous).
            confirmed: Set to true to bypass confirmation gates.

        Returns:
            The execution result as a dictionary.
        """
        # Validate/Default inputs
        if inputs is None:
            inputs = {}

        # Construct Intent
        intent = ChatIntent(
            type=IntentType.ACTION_CALL,
            request_id=str(uuid.uuid4()),
            action_id=action_id,
            inputs=inputs,
            execution_mode=ExecutionMode(mode)
            if mode
            else ExecutionMode.ASSISTED,
            confirmed=confirmed,
        )

        # Execute (using 'api_user' or similar role - assuming API caller is authorized)
        # TODO: Real auth integration for API calls
        result = self.engine.execute_intent(
            project_id=project_id,
            intent=intent,
            user_roles=[
                "admin"
            ],  # API access assumed Admin for now per docs/22_API_REFERENCE
            user_id="api_user",
        )

        return result.model_dump(mode="json")

    def execute_plan(
        self,
        project_id: str,
        plan: dict[str, Any],
        mode: str = "assisted",
    ) -> list[dict[str, Any]]:
        """Executes a multi-step plan via the engine.

        Args:
            project_id: The target project ID.
            plan: The plan dictionary (matching ExecutionPlan schema).
            mode: Execution mode (interactive, assisted, autonomous).

        Returns:
            List of execution results as dictionaries.
        """
        try:
            # Validate/Parse plan
            plan_obj = ExecutionPlan(**plan)
        except Exception as e:
            return [{"status": "failed", "message": f"Invalid plan: {str(e)}"}]

        results = self.engine.execute_plan(
            project_id=project_id,
            plan=plan_obj,
            user_roles=["admin"],
            user_id="api_user",
        )
        return [res.model_dump(mode="json") for res in results]

    def revert_snapshot(
        self, project_id: str, snapshot_id: str
    ) -> dict[str, Any]:
        """Reverts the project state to a specific snapshot.

        Args:
            project_id: The target project ID.
            snapshot_id: The snapshot ID to revert to.

        Returns:
            The execution result.
        """
        result = self.engine.revert_to_snapshot(project_id, snapshot_id)
        return result.model_dump(mode="json")

    def webhook_execute(
        self,
        webhook_id: str,
        payload: dict[str, Any],
        signature: str,
    ) -> dict[str, Any]:
        """Executes an action triggered by a webhook.

        Args:
            webhook_id: The ID of the webhook to trigger.
            payload: The JSON payload from the external system.
            signature: The signature string for verification (must match secret).

        Returns:
            The execution result.
        """
        # 1. Load config
        webhook = self.engine.repository.get_webhook(webhook_id)
        if not webhook:
            return {"status": "error", "message": "Webhook not found"}

        if not webhook.get("enabled", True):
            return {"status": "error", "message": "Webhook disabled"}

        # 2. Verify Signature (Simplification: exact match with secret)
        # In production, use HMAC-SHA256 of the raw body.
        if signature != webhook["secret"]:
            return {"status": "rejected", "message": "Invalid signature"}

        # 3. Template Rendering (Simple Key Substitution)
        inputs = {}
        template = webhook.get("inputs_template")

        if not template:
            inputs = payload
        else:
            for k, v in template.items():
                # Handle basic {{ key }} substitution
                if (
                    isinstance(v, str)
                    and v.startswith("{{")
                    and v.endswith("}}")
                ):
                    source_key = v[2:-2].strip()
                    inputs[k] = payload.get(source_key)
                else:
                    inputs[k] = v

        # 4. Execute
        intent = ChatIntent(
            type=IntentType.ACTION_CALL,
            request_id=str(uuid.uuid4()),
            action_id=webhook["action_id"],
            inputs=inputs,
            execution_mode=ExecutionMode.AUTONOMOUS,
            confirmed=True,  # Webhooks are trusted sources
            trace={"trigger": "webhook", "webhook_id": webhook_id},
        )

        result = self.engine.execute_intent(
            project_id=webhook["project_id"],
            intent=intent,
            user_roles=["admin"],
            user_id="webhook",
        )

        return result.model_dump(mode="json")

    def get_registry(self, project_id: str, user_id: str | None = None) -> dict[str, Any]:
        """Returns the current Action and Component registries.

        Args:
            project_id: The target project ID.
            user_id: Optional user ID to filter actions by visibility.

        Returns:
            Object containing components and actions declarations.
        """
        # Determine user role
        user_role = "viewer"
        if user_id:
            members = self.engine.repository.get_project_members(project_id)
            for m in members:
                if m["user_id"] == user_id:
                    user_role = m["role"]
                    break

        actions = self.engine.registry.list_actions()
        if user_role != "admin":
            actions = [
                a for a in actions 
                if a.permission.visibility != "developer"
            ]

        return {
            "components": [
                c.model_dump(mode="json")
                for c in self.engine.registry.list_components()
            ],
            "actions": [
                a.model_dump(mode="json")
                for a in actions
            ],
        }

    def get_audit_log(
        self, project_id: str, limit: int = 100
    ) -> list[dict[str, Any]]:
        """Retrieves the recent execution history for a project.

        Args:
            project_id: The target project ID.
            limit: Maximum number of records to return.

        Returns:
            A list of past execution records.
        """
        history = self.engine.repository.get_execution_history(
            project_id, limit
        )
        return [res.model_dump(mode="json") for res in history]

    def manage_project(
        self,
        op: ProjectOp,
        name: str | None = None,
        project_id: str | None = None,
    ) -> dict[str, Any]:
        """Manages the project lifecycle.

        Args:
            op: Operation (create, archive, purge).
            name: Required for create.
            project_id: Required for archive/purge.

        Returns:
            Result dictionary.
        """
        if op == ProjectOp.CREATE:
            if not name:
                return {
                    "status": "error",
                    "message": "Name required for create",
                }
            # Generate ID if not provided (though param says project_id optional, usually generated)
            pid = project_id or str(uuid.uuid4())
            self.engine.repository.create_project(pid, name)
            return {
                "status": "success",
                "project_id": pid,
                "message": "Project created",
            }

        elif op == ProjectOp.ARCHIVE:
            if not project_id:
                return {
                    "status": "error",
                    "message": "Project ID required for archive",
                }
            self.engine.repository.archive_project(project_id)
            return {"status": "success", "message": "Project archived"}

        elif op == ProjectOp.PURGE:
            if not project_id:
                return {
                    "status": "error",
                    "message": "Project ID required for purge",
                }
            self.engine.repository.purge_project(project_id)
            return {"status": "success", "message": "Project purged"}

        return {"status": "error", "message": f"Unknown operation: {op}"}

    def manage_membership(
        self,
        op: MembershipOp,
        project_id: str,
        username: str,
        role: str | None = None,
    ) -> dict[str, Any]:
        """Manages project membership.

        Args:
            op: Operation (add, remove, update_role).
            project_id: Target project.
            username: Target user (user_id).
            role: Role to assign (viewer, operator, admin).

        Returns:
            Result dictionary.
        """
        if op == MembershipOp.ADD:
            if not role:
                return {"status": "error", "message": "Role required for add"}
            self.engine.repository.add_project_member(
                project_id, username, role
            )
            return {"status": "success", "message": "Member added"}

        elif op == MembershipOp.REMOVE:
            self.engine.repository.remove_project_member(project_id, username)
            return {"status": "success", "message": "Member removed"}

        elif op == MembershipOp.UPDATE_ROLE:
            if not role:
                return {
                    "status": "error",
                    "message": "Role required for update_role",
                }
            self.engine.repository.update_project_member_role(
                project_id, username, role
            )
            return {"status": "success", "message": "Role updated"}

        return {"status": "error", "message": f"Unknown operation: {op}"}

    def manage_webhook(
        self,
        op: WebhookOp,
        webhook_id: str | None = None,
        config: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Manages webhooks.

        Args:
            op: Operation (create, update, delete).
            webhook_id: Required for update/delete.
            config: Required for create/update.

        Returns:
            Result dictionary.
        """
        if op == WebhookOp.CREATE:
            if not config:
                return {
                    "status": "error",
                    "message": "Config required for create",
                }
            if not config.get("id"):
                config["id"] = str(uuid.uuid4())
            self.engine.repository.save_webhook(config)
            return {
                "status": "success",
                "webhook_id": config["id"],
                "message": "Webhook created",
            }

        elif op == WebhookOp.UPDATE:
            if not webhook_id or not config:
                return {
                    "status": "error",
                    "message": "Webhook ID and config required for update",
                }
            config["id"] = webhook_id  # Ensure ID match
            self.engine.repository.save_webhook(config)
            return {"status": "success", "message": "Webhook updated"}

        elif op == WebhookOp.DELETE:
            if not webhook_id:
                return {
                    "status": "error",
                    "message": "Webhook ID required for delete",
                }
            self.engine.repository.delete_webhook(webhook_id)
            return {"status": "success", "message": "Webhook deleted"}

        return {"status": "error", "message": f"Unknown operation: {op}"}

    def manage_schedule(
        self,
        op: ScheduleOp,
        schedule_id: str | None = None,
        config: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Manages schedules.

        Args:
            op: Operation (create, update, delete).
            schedule_id: Required for update/delete.
            config: Required for create/update.

        Returns:
            Result dictionary.
        """
        if op == ScheduleOp.CREATE:
            if not config:
                return {
                    "status": "error",
                    "message": "Config required for create",
                }
            if not config.get("id"):
                config["id"] = str(uuid.uuid4())
            self.engine.repository.save_schedule(config)
            return {
                "status": "success",
                "schedule_id": config["id"],
                "message": "Schedule created",
            }

        elif op == ScheduleOp.UPDATE:
            if not schedule_id or not config:
                return {
                    "status": "error",
                    "message": "Schedule ID and config required for update",
                }
            config["id"] = schedule_id  # Ensure ID match
            self.engine.repository.save_schedule(config)
            return {"status": "success", "message": "Schedule updated"}

        elif op == ScheduleOp.DELETE:
            if not schedule_id:
                return {
                    "status": "error",
                    "message": "Schedule ID required for delete",
                }
            self.engine.repository.delete_schedule(schedule_id)
            return {"status": "success", "message": "Schedule deleted"}

        return {"status": "error", "message": f"Unknown operation: {op}"}

    def update_project_policy(
        self, project_id: str, policy: dict[str, Any]
    ) -> dict[str, Any]:
        """Updates project policy.

        Args:
            project_id: Target project.
            policy: Policy dictionary.

        Returns:
            Result dictionary.
        """
        self.engine.repository.set_project_limits(project_id, policy)
        return {"status": "success", "message": "Policy updated"}
