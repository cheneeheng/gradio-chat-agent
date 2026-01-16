"""Core execution logic for the Gradio Chat Agent.

This module contains the ExecutionEngine, which serves as the authoritative
gatekeeper for all state mutations. It enforces governance policies, validates
inputs, checks permissions, and records audit logs.
"""

import ast
import copy
import hashlib
import threading
import uuid
from typing import Any, Optional

import jsonschema
from pydantic import BaseModel

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
from gradio_chat_agent.models.plan import ExecutionPlan
from gradio_chat_agent.models.state_snapshot import StateSnapshot
from gradio_chat_agent.persistence.repository import StateRepository
from gradio_chat_agent.registry.abstract import Registry
from gradio_chat_agent.utils import compute_state_diff


class EngineConfig(BaseModel):
    """Configuration for the Execution Engine.

    Attributes:
        require_confirmed_for_confirmation_required: If True, strictly enforces
            the 'confirmed' flag for actions that require it.
    """

    require_confirmed_for_confirmation_required: bool = True


class ExecutionEngine:
    """The central authority for executing intents and managing state.

    The engine orchestrates the flow of:
    1. Intent validation.
    2. Permission and policy checks.
    3. State loading and locking.
    4. Action execution (via handlers).
    5. Persistence of results and snapshots.
    """

    def __init__(
        self,
        registry: Registry,
        repository: StateRepository,
        config: Optional[EngineConfig] = None,
    ):
        """Initializes the engine with necessary dependencies.

        Args:
            registry: Source of truth for component/action definitions.
            repository: Persistence layer for state and history.
            config: Optional configuration for the engine.
        """
        self.registry = registry
        self.repository = repository
        self.config = config or EngineConfig()
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

    def _is_within_execution_window(self, windows: list[dict]) -> bool:
        """Checks if the current time is within any of the allowed windows.

        Args:
            windows: A list of window dictionaries, each containing:
                - days: List of lowercase day abbreviations (mon, tue, ...).
                - hours: List of two strings [HH:MM, HH:MM] in 24h format.

        Returns:
            True if current UTC time is within an allowed window, False otherwise.
        """
        from datetime import datetime, timezone
        
        now = datetime.now(timezone.utc)
        current_day = now.strftime("%a").lower()
        current_time_str = now.strftime("%H:%M")

        for window in windows:
            allowed_days = window.get("days", [])
            if current_day not in allowed_days:
                continue
            
            allowed_hours = window.get("hours", [])
            if len(allowed_hours) == 2:
                start_str, end_str = allowed_hours
                if start_str <= current_time_str <= end_str:
                    return True
        
        return False

    def _safe_eval(self, expr: str, context: dict) -> Any:
        """Safely evaluates a Python expression using AST.

        Only allows a very restricted subset of Python:
        - Constant literals (numbers, strings, booleans, None).
        - Attribute access and Subscripting (for dict/object access).
        - Basic binary/unary operators.
        - Name lookups in the provided context.
        - NO function calls, NO comprehensions, NO imports.

        Args:
            expr: The expression string to evaluate.
            context: The variables available to the expression.

        Returns:
            The result of the evaluation.

        Raises:
            ValueError: If the expression contains forbidden nodes.
        """
        tree = ast.parse(expr, mode="eval")

        # Define allowed node types
        allowed_nodes = (
            ast.Expression,
            ast.Constant,
            ast.Name,
            ast.Load,
            ast.Attribute,
            ast.Subscript,
            ast.Index,  # For older Python versions
            ast.Slice,
            ast.BinOp,
            ast.UnaryOp,
            ast.Compare,
            ast.BoolOp,
            ast.And,
            ast.Or,
            ast.Not,
            ast.Add,
            ast.Sub,
            ast.Mult,
            ast.Div,
            ast.Mod,
            ast.Pow,
            ast.Eq,
            ast.NotEq,
            ast.Lt,
            ast.LtE,
            ast.Gt,
            ast.GtE,
            ast.Is,
            ast.IsNot,
            ast.In,
            ast.NotIn,
            ast.USub,
            ast.UAdd,
        )

        for node in ast.walk(tree):
            if not isinstance(node, allowed_nodes):
                raise ValueError(f"Forbidden expression node: {type(node).__name__}")

        # Compile and evaluate in a restricted environment
        code = compile(tree, filename="<safe_eval>", mode="eval")
        return eval(code, {"__builtins__": {}}, context)

    def execute_plan(
        self,
        project_id: str,
        plan: ExecutionPlan,
        user_roles: Optional[list[str]] = None,
        simulate: bool = False,
        user_id: Optional[str] = None,
    ) -> list[ExecutionResult]:
        """Executes a multi-step plan sequentially.

        Args:
            project_id: The ID of the project context.
            plan: The execution plan containing multiple steps.
            user_roles: List of roles held by the requesting user.
            simulate: If True, performs a dry-run without persisting changes.
            user_id: The ID of the user executing the plan.

        Returns:
            A list of ExecutionResult objects for all attempted steps.
        """
        results = []

        # Determine execution mode from first step or default
        mode = "assisted"
        if plan.steps:
            mode = plan.steps[0].execution_mode or "assisted"

        # Set limits
        max_steps = 5  # Default/Assisted
        if mode == "interactive":
            max_steps = 1
        elif mode == "autonomous":
            max_steps = 10

        if len(plan.steps) > max_steps:
            error_result = self._create_rejection(
                project_id,
                plan.steps[0],
                f"Plan exceeds step limit for {mode} mode ({len(plan.steps)} > {max_steps}).",
                code="plan_limit_exceeded",
            )
            return [error_result]

        current_simulated_state = None

        for step in plan.steps:
            # Execute the step
            result = self.execute_intent(
                project_id=project_id,
                intent=step,
                user_roles=user_roles,
                simulate=simulate,
                override_state=current_simulated_state,
                user_id=user_id,
            )
            results.append(result)

            # Abort on failure or rejection
            if result.status != ExecutionStatus.SUCCESS:
                break

            # If simulating, update the simulated state for the next step
            if simulate and result.status == ExecutionStatus.SUCCESS:
                if hasattr(result, "_simulated_state"):
                    current_simulated_state = result._simulated_state

        return results

    def execute_intent(
        self,
        project_id: str,
        intent: ChatIntent,
        user_roles: Optional[list[str]] = None,
        simulate: bool = False,
        override_state: Optional[dict] = None,
        user_id: Optional[str] = None,
    ) -> ExecutionResult:
        """Executes a single intent against a project's state.

        This method validates the intent, checks permissions, executes the
        action (if valid), and persists the result.

        Args:
            project_id: The ID of the project context.
            intent: The structured intent object to execute.
            user_roles: List of roles held by the requesting user.
                Defaults to ['viewer'].
            simulate: If True, performs a dry-run without persisting changes.
            override_state: Optional state dict to use instead of DB state (for chained simulation).
            user_id: The ID of the user executing the intent (required for memory actions).

        Returns:
            An ExecutionResult object indicating success, rejection, or failure.
        """
        if user_roles is None:
            user_roles = ["viewer"]

        # 1. Validation of Intent Structure
        if intent.type != IntentType.ACTION_CALL:
            return self._create_rejection(
                project_id, intent, "Engine only executes action_call intents."
            )

        if not intent.action_id:
            return self._create_rejection(
                project_id, intent, "Missing action_id."
            )

        # 1.3 Project Lifecycle Check
        if self.repository.is_project_archived(project_id):
            return self._create_rejection(
                project_id,
                intent,
                f"Project {project_id} is archived and does not allow executions.",
                code="project_archived",
            )

        # 1.5 Execution Window Check
        limits = self.repository.get_project_limits(project_id)
        windows = limits.get("execution_windows", {}).get("allowed")
        if windows and not simulate:
            if not self._is_within_execution_window(windows):
                return self._create_rejection(
                    project_id,
                    intent,
                    "Outside of allowed execution window.",
                    code="execution_window_violation",
                )

        # Handle Memory Actions (System Actions that write to Facts table)
        if intent.action_id in ["memory.remember", "memory.forget"]:
            if not user_id:
                return self._create_rejection(
                    project_id, intent, "User ID required for memory actions."
                )

            if simulate:
                return ExecutionResult(
                    request_id=intent.request_id,
                    action_id=intent.action_id,
                    status=ExecutionStatus.SUCCESS,
                    message="Simulated memory update.",
                    state_snapshot_id="simulated",
                    simulated=True,
                )

            inputs = intent.inputs or {}
            try:
                if intent.action_id == "memory.remember":
                    self.repository.save_session_fact(
                        project_id,
                        user_id,
                        inputs.get("key"),  # pyright: ignore[reportArgumentType]; The error will be caugt by the exception.
                        inputs.get("value"),
                    )
                    msg = f"Remembered: {inputs.get('key')} = {inputs.get('value')}"
                else:  # memory.forget
                    self.repository.delete_session_fact(
                        project_id,
                        user_id,
                        inputs.get("key"),  # pyright: ignore[reportArgumentType]; The error will be caugt by the exception.
                    )
                    msg = f"Forgot: {inputs.get('key')}"

                # Log execution, but no state diff for components
                result = ExecutionResult(
                    request_id=intent.request_id,
                    action_id=intent.action_id,
                    status=ExecutionStatus.SUCCESS,
                    message=msg,
                    state_snapshot_id="no_snapshot",  # System action
                    state_diff=[],
                )
                self.repository.save_execution(project_id, result)
                return result

            except Exception as e:
                return self._create_failure(
                    project_id, intent, f"Memory error: {str(e)}"
                )

        # 2. Acquire Lock
        lock = self._get_project_lock(project_id)
        with lock:
            # 3. Load State
            if override_state is not None:
                current_snapshot = StateSnapshot(
                    snapshot_id="simulated_prev", components=override_state
                )
            else:
                current_snapshot = self.repository.get_latest_snapshot(
                    project_id
                )
                if not current_snapshot:
                    # Initialize empty state if none exists
                    current_snapshot = StateSnapshot(
                        snapshot_id=str(uuid.uuid4()), components={}
                    )

            # 4. Resolve Action
            action = self.registry.get_action(intent.action_id)
            if not action:
                return self._create_rejection(
                    project_id, intent, f"Action {intent.action_id} not found."
                )

            # 5. Authorization & Governance
            # Fetch Limits (already fetched in 1.5, reuse if possible or re-fetch for lock safety)
            # For simplicity and freshness inside the lock, we re-fetch if needed, 
            # but let's just use the one from above for now if it's fine.
            # Actually, better re-fetch inside lock to be safe.
            limits = self.repository.get_project_limits(project_id)

            # Rate Limiting: Check actions/minute
            rpm_limit = (
                limits.get("limits", {}).get("rate", {}).get("per_minute")
            )
            if rpm_limit and not simulate:
                recent_count = self.repository.count_recent_executions(
                    project_id, minutes=1
                )
                if recent_count >= rpm_limit:
                    return self._create_rejection(
                        project_id,
                        intent,
                        f"Rate limit exceeded ({rpm_limit}/min).",
                        code="rate_limit",
                    )

            # Rate Limiting: Check actions/hour
            rph_limit = (
                limits.get("limits", {}).get("rate", {}).get("per_hour")
            )
            if rph_limit and not simulate:
                recent_count = self.repository.count_recent_executions(
                    project_id, minutes=60
                )
                if recent_count >= rph_limit:
                    return self._create_rejection(
                        project_id,
                        intent,
                        f"Hourly rate limit exceeded ({rph_limit}/hour).",
                        code="rate_limit",
                    )

            # Budget Check
            if not simulate:
                daily_budget = (
                    limits.get("limits", {}).get("budget", {}).get("daily")
                )
                if daily_budget is not None:
                    current_usage = self.repository.get_daily_budget_usage(
                        project_id
                    )
                    action_cost = getattr(action, "cost", 1.0)
                    if current_usage + action_cost > daily_budget:
                        return self._create_rejection(
                            project_id,
                            intent,
                            f"Daily budget exceeded ({current_usage:.1f} + {action_cost:.1f} > {daily_budget}).",
                            code="budget_exceeded",
                        )

            # Role check (Simple implementation: assume 'admin' has all access)
            # In a real system, we'd check action.permission against user_roles
            if (
                action.permission.risk == ActionRisk.HIGH
                and "admin" not in user_roles
            ):
                return self._create_rejection(
                    project_id,
                    intent,
                    "Insufficient permissions for high-risk action.",
                )

            # Confirmation check
            if self.config.require_confirmed_for_confirmation_required:
                if (
                    action.permission.confirmation_required
                    or action.permission.risk == ActionRisk.HIGH
                ):
                    if not intent.confirmed:
                        return self._create_rejection(
                            project_id,
                            intent,
                            "Confirmation required.",
                            code="confirmation_required",
                        )

            # Approval Workflow Check
            if not simulate and not intent.confirmed:
                approval_rules = limits.get("approvals", [])
                action_cost = getattr(action, "cost", 1.0)
                
                for rule in approval_rules:
                    min_cost = rule.get("min_cost", 0)
                    required_role = rule.get("required_role", "admin")
                    
                    if action_cost >= min_cost and required_role not in user_roles:
                        # This action triggers an approval requirement
                        result = ExecutionResult(
                            request_id=intent.request_id,
                            action_id=intent.action_id,
                            status=ExecutionStatus.PENDING_APPROVAL,
                            message=f"Action requires approval from a {required_role} (Cost: {action_cost}).",
                            state_snapshot_id="none",
                        )
                        # We save it to history so admins can see pending requests
                        self.repository.save_execution(project_id, result)
                        return result

            # 6. Schema Validation
            try:
                jsonschema.validate(
                    instance=intent.inputs or {}, schema=action.input_schema
                )
            except jsonschema.ValidationError as e:
                return self._create_rejection(
                    project_id, intent, f"Input validation failed: {e.message}"
                )

            # 7. Precondition Check
            # Safe evaluation context
            eval_context = {"state": current_snapshot.components}
            for precondition in action.preconditions:
                try:
                    if not self._safe_eval(precondition.expr, eval_context):
                        return self._create_rejection(
                            project_id,
                            intent,
                            f"Precondition failed: {precondition.description}",
                        )
                except Exception as e:
                    return self._create_rejection(
                        project_id,
                        intent,
                        f"Error evaluating precondition {precondition.id}: {str(e)}",
                    )

            # 8. Execution
            handler = self.registry.get_handler(intent.action_id)
            if not handler:
                return self._create_failure(
                    project_id,
                    intent,
                    f"No handler registered for {intent.action_id}.",
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
                return self._create_failure(
                    project_id, intent, f"Handler error: {str(e)}"
                )

            # 8.5 Invariant Check
            for component in self.registry.list_components():
                for invariant in component.invariants:
                    try:
                        if not self._safe_eval(
                            invariant.expr,
                            {"state": new_components},
                        ):
                            return self._create_failure(
                                project_id,
                                intent,
                                f"Invariant violated for {component.component_id}: {invariant.description}",
                                code="invariant_violation",
                            )
                    except Exception as e:
                        return self._create_failure(
                            project_id,
                            intent,
                            f"Error evaluating invariant for {component.component_id}: {str(e)}",
                            code="invariant_error",
                        )

            # 9. Commit
            new_snapshot_id = (
                str(uuid.uuid4()) if not simulate else "simulated"
            )

            # Media Hashing
            metadata = {}
            metadata["cost"] = getattr(action, "cost", 1.0)

            if intent.media and intent.media.data:
                media_hash = hashlib.sha256(
                    intent.media.data.encode("utf-8")
                ).hexdigest()
                metadata["media_hash"] = media_hash
                metadata["media_type"] = intent.media.type
                metadata["media_mime"] = intent.media.mime_type

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
                simulated=simulate,
                metadata=metadata,
            )

            if simulate:
                result._simulated_state = new_components
                return result

            new_snapshot = StateSnapshot(
                snapshot_id=new_snapshot_id, components=new_components
            )

            self.repository.save_snapshot(project_id, new_snapshot)
            self.repository.save_execution(project_id, result)

            return result

    def revert_to_snapshot(
        self, project_id: str, snapshot_id: str
    ) -> ExecutionResult:
        """Reverts the project state to a specific snapshot.

        This creates a new snapshot with the content of the target snapshot
        and logs a 'system.revert' execution.

        Args:
            project_id: The ID of the project.
            snapshot_id: The ID of the snapshot to revert to.

        Returns:
            The execution result of the revert operation.
        """
        lock = self._get_project_lock(project_id)
        with lock:
            # 1. Validation
            target_snapshot = self.repository.get_snapshot(snapshot_id)
            if not target_snapshot:
                return self._create_failure(
                    project_id,
                    ChatIntent(
                        type=IntentType.ACTION_CALL,
                        request_id=str(uuid.uuid4()),
                        action_id="system.revert",
                    ),
                    f"Snapshot {snapshot_id} not found.",
                    code="not_found",
                )

            current_snapshot = self.repository.get_latest_snapshot(project_id)
            if not current_snapshot:
                # Should not happen if there is a history to revert to
                current_snapshot = StateSnapshot(
                    snapshot_id="init", components={}
                )

            # 2. Revert Logic
            new_snapshot_id = str(uuid.uuid4())
            new_components = copy.deepcopy(target_snapshot.components)

            new_snapshot = StateSnapshot(
                snapshot_id=new_snapshot_id,
                components=new_components,
            )

            diffs = compute_state_diff(
                current_snapshot.components, new_components
            )

            result = ExecutionResult(
                request_id=str(uuid.uuid4()),
                action_id="system.revert",
                status=ExecutionStatus.SUCCESS,
                message=f"Reverted state to snapshot {snapshot_id}",
                state_snapshot_id=new_snapshot_id,
                state_diff=diffs,
            )

            # 3. Persistence
            self.repository.save_snapshot(project_id, new_snapshot)
            self.repository.save_execution(project_id, result)

            return result

    def _create_rejection(
        self,
        project_id: str,
        intent: ChatIntent,
        message: str,
        code: str = "policy_violation",
        snapshot_id: str = "unknown",
    ) -> ExecutionResult:
        """Helper to create AND PERSIST a REJECTED execution result.

        Args:
            project_id: The ID of the project context.
            intent: The structured intent object that was rejected.
            message: A human-readable explanation of why the intent was rejected.
            code: A machine-readable error code. Defaults to 'policy_violation'.
            snapshot_id: The ID of the state snapshot at the time of rejection.
                Defaults to 'unknown'.

        Returns:
            An ExecutionResult object with REJECTED status.
        """
        result = ExecutionResult(
            request_id=intent.request_id,
            action_id=intent.action_id or "unknown",
            status=ExecutionStatus.REJECTED,
            message=message,
            state_snapshot_id=snapshot_id,
            error=ExecutionError(code=code, detail=message),
        )
        try:
            self.repository.save_execution(project_id, result)
        except Exception:
            # In case of DB error during rejection log, we shouldn't crash the rejection response
            _ = None
        return result

    def _create_failure(
        self,
        project_id: str,
        intent: ChatIntent,
        message: str,
        code: str = "handler_error",
        snapshot_id: str = "unknown",
    ) -> ExecutionResult:
        """Helper to create AND PERSIST a FAILED execution result.

        Args:
            project_id: The ID of the project context.
            intent: The structured intent object that failed.
            message: A human-readable explanation of the failure.
            code: A machine-readable error code. Defaults to 'handler_error'.
            snapshot_id: The ID of the state snapshot at the time of failure.
                Defaults to 'unknown'.

        Returns:
            An ExecutionResult object with FAILED status.
        """
        result = ExecutionResult(
            request_id=intent.request_id,
            action_id=intent.action_id or "unknown",
            status=ExecutionStatus.FAILED,
            message=message,
            state_snapshot_id=snapshot_id,
            error=ExecutionError(code=code, detail=message),
        )
        try:
            self.repository.save_execution(project_id, result)
        except Exception:
            _ = None
        return result
