"""Core execution logic for the Gradio Chat Agent.

This module contains the ExecutionEngine, which serves as the authoritative
gatekeeper for all state mutations. It enforces governance policies, validates
inputs, checks permissions, and records audit logs.
"""

import copy
import threading
import uuid
from typing import Optional

import jsonschema

from gradio_chat_agent.models.enums import (
    ActionRisk,
    ExecutionStatus,
    IntentType,
)
from gradio_chat_agent.models.execution_result import (
    ExecutionError,
    ExecutionResult,
)
from gradio_chat_agent.models.intent import ChatIntent
from gradio_chat_agent.models.state_snapshot import StateSnapshot
from gradio_chat_agent.persistence.repository import StateRepository
from gradio_chat_agent.registry.abstract import Registry
from gradio_chat_agent.utils import compute_state_diff


class ExecutionEngine:
    """The central authority for executing intents and managing state.

    The engine orchestrates the flow of:
    1. Intent validation.
    2. Permission and policy checks.
    3. State loading and locking.
    4. Action execution (via handlers).
    5. Persistence of results and snapshots.
    """

    def __init__(self, registry: Registry, repository: StateRepository):
        """Initializes the engine with necessary dependencies.

        Args:
            registry: Source of truth for component/action definitions.
            repository: Persistence layer for state and history.
        """
        self.registry = registry
        self.repository = repository
        self.project_locks: dict[str, threading.Lock] = {}
        self._global_lock = threading.Lock()

    def _get_project_lock(self, project_id: str) -> threading.Lock:
        """Retrieves (or creates) a threading lock for a specific project.

        Args:
            project_id: The ID of the project to lock.

        Returns:
            A threading.Lock object dedicated to the project.
        """
        with self._global_lock:
            if project_id not in self.project_locks:
                self.project_locks[project_id] = threading.Lock()
            return self.project_locks[project_id]

    def execute_intent(
        self,
        project_id: str,
        intent: ChatIntent,
        user_roles: Optional[list[str]] = None,
    ) -> ExecutionResult:
        """Executes a single intent against a project's state.

        This method validates the intent, checks permissions, executes the
        action (if valid), and persists the result.

        Args:
            project_id: The ID of the project context.
            intent: The structured intent object to execute.
            user_roles: List of roles held by the requesting user.
                        Defaults to ['viewer'].

        Returns:
            An ExecutionResult object indicating success, rejection, or failure.
        """
        if user_roles is None:
            user_roles = ["viewer"]

        # 1. Validation of Intent Structure
        if intent.type != IntentType.ACTION_CALL:
            return self._create_rejection(
                intent, "Engine only executes action_call intents."
            )

        if not intent.action_id:
            return self._create_rejection(intent, "Missing action_id.")

        # 2. Acquire Lock
        lock = self._get_project_lock(project_id)
        with lock:
            # 3. Load State
            current_snapshot = self.repository.get_latest_snapshot(project_id)
            if not current_snapshot:
                # Initialize empty state if none exists
                current_snapshot = StateSnapshot(
                    snapshot_id=str(uuid.uuid4()), components={}
                )

            # 4. Resolve Action
            action = self.registry.get_action(intent.action_id)
            if not action:
                return self._create_rejection(
                    intent, f"Action {intent.action_id} not found."
                )

            # 5. Authorization & Governance
            # Role check (Simple implementation: assume 'admin' has all access)
            # In a real system, we'd check action.permission against user_roles
            if (
                action.permission.risk == ActionRisk.HIGH
                and "admin" not in user_roles
            ):
                return self._create_rejection(
                    intent, "Insufficient permissions for high-risk action."
                )

            # Confirmation check
            if (
                action.permission.confirmation_required
                or action.permission.risk == ActionRisk.HIGH
            ):
                if not intent.confirmed:
                    return self._create_rejection(
                        intent,
                        "Confirmation required.",
                        code="confirmation_required",
                    )

            # 6. Schema Validation
            try:
                jsonschema.validate(
                    instance=intent.inputs or {}, schema=action.input_schema
                )
            except jsonschema.ValidationError as e:
                return self._create_rejection(
                    intent, f"Input validation failed: {e.message}"
                )

            # 7. Precondition Check
            # Safe evaluation context
            eval_context = {"state": current_snapshot.components}
            for precondition in action.preconditions:
                try:
                    # WARNING: eval is used here. Ensure registry sources are trusted.
                    # In production, use a RestrictedPython or AST-based evaluator.
                    if not eval(
                        precondition.expr, {"__builtins__": {}}, eval_context
                    ):
                        return self._create_rejection(
                            intent,
                            f"Precondition failed: {precondition.description}",
                        )
                except Exception as e:
                    return self._create_rejection(
                        intent,
                        f"Error evaluating precondition {precondition.id}: {str(e)}",
                    )

            # 8. Execution
            handler = self.registry.get_handler(intent.action_id)
            if not handler:
                return self._create_failure(
                    intent, f"No handler registered for {intent.action_id}."
                )

            try:
                # Deep copy components to prevent mutation of the old snapshot object
                # if the handler mutates in place (though handlers should be pure-ish)
                components_copy = copy.deepcopy(current_snapshot.components)

                # Create a temporary snapshot object for the handler to read
                temp_snapshot = StateSnapshot(
                    snapshot_id=current_snapshot.snapshot_id,
                    timestamp=current_snapshot.timestamp,
                    components=components_copy,
                )

                new_components, diffs, message = handler(
                    intent.inputs or {}, temp_snapshot
                )
            except Exception as e:
                return self._create_failure(intent, f"Handler error: {str(e)}")

            # 9. Commit
            new_snapshot_id = str(uuid.uuid4())
            new_snapshot = StateSnapshot(
                snapshot_id=new_snapshot_id, components=new_components
            )

            # Re-compute diffs if handler didn't provide them reliably,
            # or just trust the handler. The Utils function is safer.
            computed_diffs = compute_state_diff(
                current_snapshot.components, new_components
            )

            result = ExecutionResult(
                request_id=intent.request_id,
                action_id=intent.action_id,
                status=ExecutionStatus.SUCCESS,
                message=message or "Action executed successfully.",
                state_snapshot_id=new_snapshot_id,
                state_diff=computed_diffs,
            )

            self.repository.save_snapshot(project_id, new_snapshot)
            self.repository.save_execution(project_id, result)

            return result

    def _create_rejection(
        self,
        intent: ChatIntent,
        message: str,
        code: str = "policy_violation",
        snapshot_id: str = "unknown",
    ) -> ExecutionResult:
        """Helper to create a REJECTED execution result."""
        return ExecutionResult(
            request_id=intent.request_id,
            action_id=intent.action_id or "unknown",
            status=ExecutionStatus.REJECTED,
            message=message,
            state_snapshot_id=snapshot_id,
            error=ExecutionError(code=code, detail=message),
        )

    def _create_failure(
        self,
        intent: ChatIntent,
        message: str,
        code: str = "handler_error",
        snapshot_id: str = "unknown",
    ) -> ExecutionResult:
        """Helper to create a FAILED execution result."""
        return ExecutionResult(
            request_id=intent.request_id,
            action_id=intent.action_id or "unknown",
            status=ExecutionStatus.FAILED,
            message=message,
            state_snapshot_id=snapshot_id,
            error=ExecutionError(code=code, detail=message),
        )