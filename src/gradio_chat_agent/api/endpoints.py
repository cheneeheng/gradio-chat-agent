"""API Endpoints implementation for the Gradio Chat Agent.

This module defines the logic for the headless API endpoints exposed via Gradio.
"""

import hashlib
import hmac
import uuid
from datetime import datetime
from typing import Any

from gradio_chat_agent.execution.engine import ExecutionEngine
from gradio_chat_agent.models.api import ApiResponse
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

        return ApiResponse(
            code=0 if result.status == "success" else 1,
            message=result.message or result.status,
            data=result.model_dump(mode="json"),
        ).model_dump(mode="json")

    def simulate_action(
        self,
        project_id: str,
        action_id: str,
        inputs: dict[str, Any],
        mode: str = "assisted",
    ) -> dict[str, Any]:
        """Simulates a single action via the engine.

        Args:
            project_id: The target project ID.
            action_id: The identifier of the action to execute.
            inputs: A dictionary of arguments matching the action's input schema.
            mode: Execution mode.

        Returns:
            The execution result wrapped in ApiResponse (simulated=True).
        """
        if inputs is None:
            inputs = {}

        intent = ChatIntent(
            type=IntentType.ACTION_CALL,
            request_id=str(uuid.uuid4()),
            action_id=action_id,
            inputs=inputs,
            execution_mode=ExecutionMode(mode)
            if mode
            else ExecutionMode.ASSISTED,
        )

        result = self.engine.execute_intent(
            project_id=project_id,
            intent=intent,
            user_roles=["admin"],
            user_id="api_user",
            simulate=True,
        )

        return ApiResponse(
            code=0 if result.status == "success" else 1,
            message=result.message or result.status,
            data=result.model_dump(mode="json"),
        ).model_dump(mode="json")

    def execute_plan(
        self,
        project_id: str,
        plan: dict[str, Any],
        mode: str = "assisted",
    ) -> dict[str, Any]:
        """Executes a multi-step plan via the engine.

        Args:
            project_id: The target project ID.
            plan: The plan dictionary (matching ExecutionPlan schema).
            mode: Execution mode (interactive, assisted, autonomous).

        Returns:
            Execution results wrapped in ApiResponse.
        """
        try:
            # Validate/Parse plan
            plan_obj = ExecutionPlan(**plan)
        except Exception as e:
            return ApiResponse(
                code=1, message=f"Invalid plan: {str(e)}"
            ).model_dump(mode="json")

        results = self.engine.execute_plan(
            project_id=project_id,
            plan=plan_obj,
            user_roles=["admin"],
            user_id="api_user",
        )

        all_success = all(res.status == "success" for res in results)

        return ApiResponse(
            code=0 if all_success else 1,
            message="Plan executed"
            if all_success
            else "Plan execution partially failed or rejected",
            data=[res.model_dump(mode="json") for res in results],
        ).model_dump(mode="json")

    def simulate_plan(
        self,
        project_id: str,
        plan: dict[str, Any],
        mode: str = "assisted",
    ) -> dict[str, Any]:
        """Simulates a multi-step plan via the engine.

        Args:
            project_id: The target project ID.
            plan: The plan dictionary.
            mode: Execution mode.

        Returns:
            Execution results wrapped in ApiResponse (simulated=True).
        """
        try:
            plan_obj = ExecutionPlan(**plan)
        except Exception as e:
            return ApiResponse(
                code=1, message=f"Invalid plan: {str(e)}"
            ).model_dump(mode="json")

        results = self.engine.execute_plan(
            project_id=project_id,
            plan=plan_obj,
            user_roles=["admin"],
            user_id="api_user",
            simulate=True,
        )

        all_success = all(res.status == "success" for res in results)

        return ApiResponse(
            code=0 if all_success else 1,
            message="Plan simulated"
            if all_success
            else "Plan simulation partially failed or rejected",
            data=[res.model_dump(mode="json") for res in results],
        ).model_dump(mode="json")

    def revert_snapshot(
        self, project_id: str, snapshot_id: str
    ) -> dict[str, Any]:
        """Reverts the project state to a specific snapshot.

        Args:
            project_id: The target project ID.
            snapshot_id: The snapshot ID to revert to.

        Returns:
            The execution result wrapped in ApiResponse.
        """
        result = self.engine.revert_to_snapshot(project_id, snapshot_id)
        return ApiResponse(
            code=0 if result.status == "success" else 1,
            message=result.message or result.status,
            data=result.model_dump(mode="json"),
        ).model_dump(mode="json")

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
            return ApiResponse(code=1, message="Webhook not found").model_dump(
                mode="json"
            )

        if not webhook.get("enabled", True):
            return ApiResponse(code=1, message="Webhook disabled").model_dump(
                mode="json"
            )

        # 2. Verify Signature using HMAC-SHA256
        import json

        payload_bytes = json.dumps(payload, sort_keys=True).encode("utf-8")
        secret_bytes = webhook["secret"].encode("utf-8")
        expected_signature = hmac.new(
            secret_bytes, payload_bytes, hashlib.sha256
        ).hexdigest()

        if not hmac.compare_digest(signature, expected_signature):
            return ApiResponse(code=1, message="Invalid signature").model_dump(
                mode="json"
            )

        # 3. Template Rendering (Jinja2)
        from jinja2 import BaseLoader, Environment

        env = Environment(loader=BaseLoader())

        inputs = {}
        template_dict = webhook.get("inputs_template")

        if not template_dict:
            inputs = payload
        else:
            try:
                for k, v in template_dict.items():
                    if isinstance(v, str):
                        # Render string values as Jinja2 templates
                        t = env.from_string(v)
                        rendered = t.render(**payload)
                        # Attempt to parse as JSON if it looks like a number or boolean
                        if rendered.lower() == "true":
                            inputs[k] = True
                        elif rendered.lower() == "false":
                            inputs[k] = False
                        else:
                            try:
                                if "." in rendered:
                                    inputs[k] = float(rendered)
                                else:
                                    inputs[k] = int(rendered)
                            except ValueError:
                                inputs[k] = rendered
                    else:
                        inputs[k] = v
            except Exception as e:
                return ApiResponse(
                    code=1, message=f"Template rendering error: {str(e)}"
                ).model_dump(mode="json")

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

        return ApiResponse(
            code=0 if result.status == "success" else 1,
            message=result.message or result.status,
            data=result.model_dump(mode="json"),
        ).model_dump(mode="json")

    def get_registry(
        self, project_id: str, user_id: str | None = None
    ) -> dict[str, Any]:
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
                a for a in actions if a.permission.visibility != "developer"
            ]

        return ApiResponse(
            data={
                "components": [
                    c.model_dump(mode="json")
                    for c in self.engine.registry.list_components()
                ],
                "actions": [a.model_dump(mode="json") for a in actions],
            }
        ).model_dump(mode="json")

    def get_audit_log(
        self, project_id: str, limit: int = 100
    ) -> dict[str, Any]:
        """Retrieves the recent execution history for a project.

        Args:
            project_id: The target project ID.
            limit: Maximum number of records to return.

        Returns:
            Execution history wrapped in ApiResponse.
        """
        history = self.engine.repository.get_execution_history(
            project_id, limit
        )
        return ApiResponse(
            data=[res.model_dump(mode="json") for res in history]
        ).model_dump(mode="json")

    def _is_system_admin(self, user_id: str | None) -> bool:
        """Checks if the user has platform-wide management authority."""
        return user_id == "admin"

    def manage_project(
        self,
        op: ProjectOp,
        name: str | None = None,
        project_id: str | None = None,
        user_id: str | None = None,
        confirmed: bool = False,
    ) -> dict[str, Any]:
        """Manages the project lifecycle.

        Args:
            op: Operation (create, archive, purge).
            name: Required for create.
            project_id: Required for archive/purge.
            user_id: ID of the user performing the operation.
            confirmed: Must be True for destructive operations like PURGE.

        Returns:
            Result wrapped in ApiResponse.
        """
        if not self._is_system_admin(user_id):
            return ApiResponse(
                code=1, message="Permission denied: System Admin required"
            ).model_dump(mode="json")

        if op == ProjectOp.CREATE:
            if not name:
                return ApiResponse(
                    code=1, message="Name required for create"
                ).model_dump(mode="json")
            # Generate ID if not provided
            pid = project_id or str(uuid.uuid4())
            self.engine.repository.create_project(pid, name)

            # --- Policy Templating: Apply default limits ---
            default_policy = {
                "limits": {
                    "rate": {"per_minute": 10, "per_hour": 200},
                    "budget": {"daily": 500.0},
                }
            }
            self.engine.repository.set_project_limits(pid, default_policy)

            return ApiResponse(
                message="Project created with default policy",
                data={"project_id": pid, "policy": default_policy},
            ).model_dump(mode="json")

        elif op == ProjectOp.ARCHIVE:
            if not project_id:
                return ApiResponse(
                    code=1, message="Project ID required for archive"
                ).model_dump(mode="json")
            self.engine.repository.archive_project(project_id)
            return ApiResponse(message="Project archived").model_dump(
                mode="json"
            )

        elif op == ProjectOp.PURGE:
            if not project_id:
                return ApiResponse(
                    code=1, message="Project ID required for purge"
                ).model_dump(mode="json")

            # --- Purge Confirmation Gate ---
            if not confirmed:
                return ApiResponse(
                    code=1,
                    message="Confirmation required for destructive PURGE operation. Please set confirmed=true.",
                ).model_dump(mode="json")

            self.engine.repository.purge_project(project_id)
            return ApiResponse(message="Project purged").model_dump(
                mode="json"
            )

        return ApiResponse(
            code=1, message=f"Unknown operation: {op}"
        ).model_dump(mode="json")

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
            Result wrapped in ApiResponse.
        """
        if op == MembershipOp.ADD:
            if not role:
                return ApiResponse(
                    code=1, message="Role required for add"
                ).model_dump(mode="json")
            self.engine.repository.add_project_member(
                project_id, username, role
            )
            return ApiResponse(message="Member added").model_dump(mode="json")

        elif op == MembershipOp.REMOVE:
            self.engine.repository.remove_project_member(project_id, username)
            return ApiResponse(message="Member removed").model_dump(
                mode="json"
            )

        elif op == MembershipOp.UPDATE_ROLE:
            if not role:
                return ApiResponse(
                    code=1, message="Role required for update_role"
                ).model_dump(mode="json")
            self.engine.repository.update_project_member_role(
                project_id, username, role
            )
            return ApiResponse(message="Role updated").model_dump(mode="json")

        return ApiResponse(
            code=1, message=f"Unknown operation: {op}"
        ).model_dump(mode="json")

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
            Result wrapped in ApiResponse.
        """
        if op == WebhookOp.CREATE:
            if not config:
                return ApiResponse(
                    code=1, message="Config required for create"
                ).model_dump(mode="json")
            if not config.get("id"):
                config["id"] = str(uuid.uuid4())
            self.engine.repository.save_webhook(config)
            return ApiResponse(
                message="Webhook created",
                data={"webhook_id": config["id"]},
            ).model_dump(mode="json")

        elif op == WebhookOp.UPDATE:
            if not webhook_id or not config:
                return ApiResponse(
                    code=1, message="Webhook ID and config required for update"
                ).model_dump(mode="json")
            config["id"] = webhook_id  # Ensure ID match
            self.engine.repository.save_webhook(config)
            return ApiResponse(message="Webhook updated").model_dump(
                mode="json"
            )

        elif op == WebhookOp.DELETE:
            if not webhook_id:
                return ApiResponse(
                    code=1, message="Webhook ID required for delete"
                ).model_dump(mode="json")
            self.engine.repository.delete_webhook(webhook_id)
            return ApiResponse(message="Webhook deleted").model_dump(
                mode="json"
            )

        return ApiResponse(
            code=1, message=f"Unknown operation: {op}"
        ).model_dump(mode="json")

    def rotate_webhook_secret(
        self, webhook_id: str, new_secret: str | None = None
    ) -> dict[str, Any]:
        """Rotates the secret for a webhook.

        Args:
            webhook_id: The ID of the webhook.
            new_secret: Optional new secret. If not provided, a random one is generated.

        Returns:
            Result wrapped in ApiResponse.
        """
        secret = new_secret or str(uuid.uuid4())
        self.engine.repository.rotate_webhook_secret(webhook_id, secret)
        return ApiResponse(
            message="Webhook secret rotated", data={"new_secret": secret}
        ).model_dump(mode="json")

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
            Result wrapped in ApiResponse.
        """
        if op == ScheduleOp.CREATE:
            if not config:
                return ApiResponse(
                    code=1, message="Config required for create"
                ).model_dump(mode="json")
            if not config.get("id"):
                config["id"] = str(uuid.uuid4())
            self.engine.repository.save_schedule(config)
            return ApiResponse(
                message="Schedule created",
                data={"schedule_id": config["id"]},
            ).model_dump(mode="json")

        elif op == ScheduleOp.UPDATE:
            if not schedule_id or not config:
                return ApiResponse(
                    code=1,
                    message="Schedule ID and config required for update",
                ).model_dump(mode="json")
            config["id"] = schedule_id  # Ensure ID match
            self.engine.repository.save_schedule(config)
            return ApiResponse(message="Schedule updated").model_dump(
                mode="json"
            )

        elif op == ScheduleOp.DELETE:
            if not schedule_id:
                return ApiResponse(
                    code=1, message="Schedule ID required for delete"
                ).model_dump(mode="json")
            self.engine.repository.delete_schedule(schedule_id)
            return ApiResponse(message="Schedule deleted").model_dump(
                mode="json"
            )

        return ApiResponse(
            code=1, message=f"Unknown operation: {op}"
        ).model_dump(mode="json")

    def update_project_policy(
        self, project_id: str, policy: dict[str, Any]
    ) -> dict[str, Any]:
        """Updates project policy.

        Args:
            project_id: Target project.
            policy: Policy dictionary.

        Returns:
            Result wrapped in ApiResponse.
        """
        self.engine.repository.set_project_limits(project_id, policy)
        return ApiResponse(message="Policy updated").model_dump(mode="json")

    def list_users(self, user_id: str | None = None) -> dict[str, Any]:
        """Lists all users in the system.

        Args:
            user_id: ID of the user performing the operation.

        Returns:
            List of users wrapped in ApiResponse.
        """
        if not self._is_system_admin(user_id):
            return ApiResponse(
                code=1, message="Permission denied: System Admin required"
            ).model_dump(mode="json")

        users = self.engine.repository.list_users()
        return ApiResponse(
            data=[
                {
                    "id": u["id"],
                    "full_name": u.get("full_name"),
                    "email": u.get("email"),
                    "organization_id": u.get("organization_id"),
                    "created_at": u["created_at"].isoformat()
                    if isinstance(u["created_at"], datetime)
                    else u["created_at"],
                }
                for u in users
            ]
        ).model_dump(mode="json")

    def delete_user(
        self, target_user_id: str, user_id: str | None = None
    ) -> dict[str, Any]:
        """Deletes a user from the system.

        Args:
            target_user_id: The ID of the user to delete.
            user_id: ID of the user performing the operation.

        Returns:
            Result wrapped in ApiResponse.
        """
        if not self._is_system_admin(user_id):
            return ApiResponse(
                code=1, message="Permission denied: System Admin required"
            ).model_dump(mode="json")

        self.engine.repository.delete_user(target_user_id)
        return ApiResponse(
            message=f"User {target_user_id} deleted"
        ).model_dump(mode="json")

    def budget_forecast(self, project_id: str) -> dict[str, Any]:
        """Returns budget usage stats and exhaustion predictions for a project.

        Args:
            project_id: The target project ID.

        Returns:
            Forecast data wrapped in ApiResponse.
        """
        from gradio_chat_agent.execution.forecasting import ForecastingService

        service = ForecastingService(self.engine)
        forecast = service.get_budget_forecast(project_id)
        return ApiResponse(data=forecast).model_dump(mode="json")

    def api_org_rollup(self, user_id: str | None = None) -> dict[str, Any]:
        """Provides a summary of all projects and platform-wide stats.

        Args:
            user_id: ID of the user performing the operation (must be system admin).

        Returns:
            Rollup data wrapped in ApiResponse.
        """
        if not self._is_system_admin(user_id):
            return ApiResponse(
                code=1, message="Permission denied: System Admin required"
            ).model_dump(mode="json")

        rollup = self.engine.repository.get_org_rollup()
        return ApiResponse(data=rollup).model_dump(mode="json")

    def create_api_token(
        self,
        owner_user_id: str,
        name: str,
        user_id: str | None = None,
        expires_in_days: int | None = None,
    ) -> dict[str, Any]:
        """Creates a new API token.

        Args:
            owner_user_id: The user ID who will own the token.
            name: Label for the token.
            user_id: The ID of the admin performing the operation.
            expires_in_days: Optional validity period.

        Returns:
            The generated token wrapped in ApiResponse.
        """
        if not self._is_system_admin(user_id):
            return ApiResponse(
                code=1, message="Permission denied: System Admin required"
            ).model_dump(mode="json")

        token_id = f"sk-{uuid.uuid4().hex}"
        expires_at = None
        if expires_in_days:
            from datetime import timedelta

            expires_at = datetime.utcnow() + timedelta(days=expires_in_days)

        self.engine.repository.create_api_token(
            owner_user_id, name, token_id, expires_at
        )

        return ApiResponse(
            message="API token created",
            data={
                "token": token_id,
                "name": name,
                "owner": owner_user_id,
                "expires_at": expires_at.isoformat() if expires_at else None,
            },
        ).model_dump(mode="json")

    def list_api_tokens(
        self, owner_user_id: str, user_id: str | None = None
    ) -> dict[str, Any]:
        """Lists API tokens for a user.

        Args:
            owner_user_id: The user to list tokens for.
            user_id: The ID of the admin performing the operation.

        Returns:
            List of tokens wrapped in ApiResponse.
        """
        if not self._is_system_admin(user_id) and user_id != owner_user_id:
            return ApiResponse(
                code=1, message="Permission denied"
            ).model_dump(mode="json")

        tokens = self.engine.repository.list_api_tokens(owner_user_id)
        return ApiResponse(data=tokens).model_dump(mode="json")

    def revoke_api_token(
        self, token_id: str, user_id: str | None = None
    ) -> dict[str, Any]:
        """Revokes an API token.

        Args:
            token_id: The token to revoke.
            user_id: The ID of the admin performing the operation.

        Returns:
            Success message wrapped in ApiResponse.
        """
        if not self._is_system_admin(user_id):
            # In a real system, owners should be able to revoke their own tokens.
            # For simplicity, we stick to system admin for now.
            return ApiResponse(
                code=1, message="Permission denied: System Admin required"
            ).model_dump(mode="json")

        self.engine.repository.revoke_api_token(token_id)
        return ApiResponse(message="API token revoked").model_dump(mode="json")
