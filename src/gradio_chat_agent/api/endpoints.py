"""API Endpoints implementation for the Gradio Chat Agent.

This module defines the logic for the headless API endpoints exposed via Gradio.
"""

import uuid
from typing import Any

from gradio_chat_agent.execution.engine import ExecutionEngine
from gradio_chat_agent.models.enums import ExecutionMode, IntentType
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
        )

        return result.model_dump(mode="json")

    def get_registry(self, project_id: str) -> dict[str, Any]:
        """Returns the current Action and Component registries.

        Args:
            project_id: The target project ID (unused for now as registry is global/static
                        in this version, but kept for API compat).

        Returns:
            Object containing components and actions declarations.
        """
        return {
            "components": [
                c.model_dump(mode="json")
                for c in self.engine.registry.list_components()
            ],
            "actions": [
                a.model_dump(mode="json")
                for a in self.engine.registry.list_actions()
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
