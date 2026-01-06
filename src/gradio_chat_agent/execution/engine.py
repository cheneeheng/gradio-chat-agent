from datetime import datetime, timezone
from typing import Any, Callable, Optional

import jsonschema
from pydantic import BaseModel, ConfigDict, Field

from ..models.action import ActionDeclaration
from ..models.execution_result import (
    ExecutionError,
    ExecutionResult,
    StateDiffEntry,
)
from ..models.intent import ChatIntent
from ..models.state_snapshot import StateSnapshot
from .alerts import evaluate_budget_alerts
from .approvals import requires_human_approval
from .authority import is_viewer_only, normalize_roles
from .cost import compute_action_cost
from .limits import LimitViolation, enforce_action_budget
from .modes import ExecutionContext, ExecutionMode, ModePolicy
from .plan import ExecutionPlan
from .preconditions import check_preconditions
from .throttle import throttle_if_needed


class EngineConfig(BaseModel):
    """
    Static configuration for the execution engine.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    require_confirmed_for_confirmation_required: bool = Field(
        default=True,
        description="Whether confirmation_required actions must have intent.confirmed=True.",
    )


class EngineStateStore(BaseModel):
    """
    Central mutable state store backing the UI.
    """

    model_config = ConfigDict(extra="forbid")

    snapshot: StateSnapshot = Field(
        ...,
        description="Current application state snapshot.",
    )

    def apply(
        self, new_components: dict[str, dict[str, Any]]
    ) -> StateSnapshot:
        self.snapshot = StateSnapshot(
            snapshot_id=f"snap_{datetime.now(timezone.utc).isoformat()}",
            timestamp=datetime.now(timezone.utc),
            components=new_components,
        )
        return self.snapshot


ActionHandler = Callable[
    [dict[str, Any], StateSnapshot],
    tuple[dict[str, dict[str, Any]], list[StateDiffEntry], str],
]


class ExecutionEngine:
    """
    Validates and executes action_call intents against the action registry and current state snapshot.
    """

    def __init__(
        self,
        *,
        action_registry: dict[str, ActionDeclaration],
        handlers: dict[str, ActionHandler],
        config: Optional[EngineConfig] = None,
    ) -> None:
        self._actions = action_registry
        self._handlers = handlers
        self._config = config or EngineConfig()

    def _enforce_limits(self, ctx, action):
        limits = self.repo.get_project_limits(ctx.project_id)
        if not limits:
            return

        now = datetime.now(timezone.utc)

        # reset daily budget
        if limits.budget_reset_at is None or now >= limits.budget_reset_at:
            limits.budget_used_today = 0
            limits.budget_reset_at = now.replace(
                hour=0, minute=0, second=0
            ) + timedelta(days=1)

        cost = compute_action_cost(action)

        if limits.daily_budget is not None:
            if limits.budget_used_today + cost > limits.daily_budget:
                raise LimitViolation(
                    "budget.exceeded",
                    f"Daily budget exceeded ({limits.budget_used_today}/{limits.daily_budget})",
                )

        limits.budget_used_today += cost
        self.repo.save_project_limits(limits)

        if limits.max_actions_per_minute:
            count = self.repo.count_executions_since(
                ctx.project_id,
                now - timedelta(minutes=1),
            )
            if count >= limits.max_actions_per_minute:
                raise LimitViolation(
                    "rate.minute", "Too many actions per minute"
                )

    def execute_plan(
        self,
        *,
        plan: ExecutionPlan,
        mode: ExecutionMode,
        store: EngineStateStore,
    ) -> list[ExecutionResult]:
        policy = ModePolicy.for_mode(mode)
        ctx = ExecutionContext(
            policy=policy, step_index=0, plan_id=plan.plan_id
        )

        results: list[ExecutionResult] = []
        for step in plan.steps:
            ctx.validate_step_limit()

            if step.execution_mode is None:
                step = step.model_copy(update={"execution_mode": policy.mode})

            result = self.execute_intent(ctx=ctx, intent=step, store=store)
            results.append(result)

            ctx = ctx.next_step()

            if result.status in ("failed", "rejected"):
                break

        return results

    def execute_intent(
        self,
        *,
        ctx: ExecutionContext,
        intent: ChatIntent,
        store: EngineStateStore,
    ) -> ExecutionResult:
        now = datetime.now(timezone.utc)

        ctx.validate_step_limit()

        # if project.archived_at is not None:
        #     return reject(
        #         code="project.archived",
        #         detail="Project is archived and cannot execute actions",
        #     )

        if intent.type != "action_call":
            return ExecutionResult(
                request_id=intent.request_id,
                action_id="(none)",
                status="rejected",
                timestamp=datetime.now(timezone.utc),
                message="Non-action intents are not executable",
                state_snapshot_id=store.snapshot.snapshot_id,
                state_diff=[],
                error=ExecutionError(
                    code="intent.not_executable",
                    detail=f"Intent type: {intent.type}",
                ),
            )

        action = self._actions.get(intent.action_id or "")
        if not action:
            return ExecutionResult(
                request_id=intent.request_id,
                action_id=intent.action_id or "(missing)",
                status="rejected",
                timestamp=datetime.now(timezone.utc),
                message="Unknown action",
                state_snapshot_id=store.snapshot.snapshot_id,
                state_diff=[],
                error=ExecutionError(
                    code="action.unknown",
                    detail=f"Action not in registry: {intent.action_id}",
                ),
            )

        user_roles = normalize_roles(set(ctx.user_roles or []))
        # Absolute gate: viewers can never execute
        if is_viewer_only(user_roles):
            return ExecutionResult(
                request_id=intent.request_id,
                action_id=intent.action_id,
                status="rejected",
                timestamp=datetime.now(timezone.utc),
                message="Execution not permitted for viewer role",
                state_snapshot_id=store.snapshot.snapshot_id,
                state_diff=[],
                error=ExecutionError(
                    code="permission.viewer",
                    detail="Users with viewer role cannot execute actions",
                ),
            )

        required = set(action.permission.required_roles or set())
        if required and not (required & user_roles):
            have = set(ctx.user_roles or [])
            if not (required & have) and "admin" not in have:
                return ExecutionResult(
                    request_id=intent.request_id,
                    action_id=action.action_id,
                    status="rejected",
                    timestamp=datetime.now(timezone.utc),
                    message="Not authorized",
                    state_snapshot_id=store.snapshot.snapshot_id,
                    state_diff=[],
                    error=ExecutionError(
                        code="permission.denied",
                        detail=f"Requires one of roles: {sorted(required)}; user has: {sorted(have)}",
                    ),
                )

        # Confirmation gate
        if (
            action.permission.confirmation_required
            and self._config.require_confirmed_for_confirmation_required
        ):
            if not intent.confirmed:
                return ExecutionResult(
                    request_id=intent.request_id,
                    action_id=action.action_id,
                    status="rejected",
                    timestamp=datetime.now(timezone.utc),
                    message="Confirmation required",
                    state_snapshot_id=store.snapshot.snapshot_id,
                    state_diff=[],
                    error=ExecutionError(
                        code="permission.confirmation_required",
                        detail="Action requires confirmation; intent.confirmed must be true.",
                    ),
                )

        # High-risk gate (all modes)
        if (
            ctx.policy.require_confirmation_for_high_risk
            and action.permission.risk == "high"
        ):
            if not intent.confirmed:
                return ExecutionResult(
                    request_id=intent.request_id,
                    action_id=action.action_id,
                    status="rejected",
                    timestamp=datetime.now(timezone.utc),
                    message="High-risk action requires confirmation",
                    state_snapshot_id=store.snapshot.snapshot_id,
                    state_diff=[],
                    error=ExecutionError(
                        code="permission.high_risk_confirmation_required",
                        detail="High-risk actions require explicit confirmation in all modes.",
                    ),
                )

        # Input schema validation
        try:
            jsonschema.validate(
                instance=intent.inputs or {}, schema=action.input_schema
            )
        except jsonschema.ValidationError as e:
            return ExecutionResult(
                request_id=intent.request_id,
                action_id=action.action_id,
                status="rejected",
                timestamp=datetime.now(timezone.utc),
                message="Invalid action inputs",
                state_snapshot_id=store.snapshot.snapshot_id,
                state_diff=[],
                error=ExecutionError(code="input.invalid", detail=str(e)),
            )

        # Preconditions
        failures = check_preconditions(action.preconditions, store.snapshot)
        if failures:
            detail = "; ".join(
                [f"{f.precondition_id}: {f.detail}" for f in failures]
            )
            return ExecutionResult(
                request_id=intent.request_id,
                action_id=action.action_id,
                status="rejected",
                timestamp=datetime.now(timezone.utc),
                message="Preconditions not met",
                state_snapshot_id=store.snapshot.snapshot_id,
                state_diff=[],
                error=ExecutionError(
                    code="precondition.failed", detail=detail
                ),
            )

        handler = self._handlers.get(action.action_id)
        if not handler:
            return ExecutionResult(
                request_id=intent.request_id,
                action_id=action.action_id,
                status="failed",
                timestamp=datetime.now(timezone.utc),
                message="No handler registered",
                state_snapshot_id=store.snapshot.snapshot_id,
                state_diff=[],
                error=ExecutionError(
                    code="handler.missing",
                    detail=f"No handler for: {action.action_id}",
                ),
            )

        try:
            self._enforce_limits(ctx, action)
            enforce_action_budget(
                self.repo,
                ctx.project_id,
                action.action_id,
                compute_action_cost(action),
                now,
            )
        except LimitViolation as e:
            if e.code.startswith("rate."):
                throttle_if_needed(e.code)
            else:
                return ExecutionResult(
                    request_id=intent.request_id,
                    action_id=intent.action_id,
                    status="rejected",
                    timestamp=now,
                    message="Execution blocked by project limits",
                    state_snapshot_id=store.snapshot.snapshot_id,
                    state_diff=[],
                    error=ExecutionError(code=e.code, detail=e.detail),
                )

        if requires_human_approval(
            self.repo, ctx.project_id, cost, set(ctx.user_roles)
        ):
            return ExecutionResult(
                request_id=intent.request_id,
                action_id=intent.action_id,
                status="pending_approval",
                timestamp=now,
                message="Execution requires human approval due to cost threshold",
                state_snapshot_id=store.snapshot.snapshot_id,
                state_diff=[],
                error=None,
            )

        try:
            new_components, diff, msg = handler(
                intent.inputs or {}, store.snapshot
            )
            new_snapshot = store.apply(new_components)
            evaluate_budget_alerts(self.repo, ctx.project_id)
            return ExecutionResult(
                request_id=intent.request_id,
                action_id=action.action_id,
                status="success",
                timestamp=datetime.now(timezone.utc),
                message=msg,
                state_snapshot_id=new_snapshot.snapshot_id,
                state_diff=diff,
                error=None,
            )
        except Exception as e:
            return ExecutionResult(
                request_id=intent.request_id,
                action_id=action.action_id,
                status="failed",
                timestamp=datetime.now(timezone.utc),
                message="Execution failed",
                state_snapshot_id=store.snapshot.snapshot_id,
                state_diff=[],
                error=ExecutionError(
                    code="execution.exception", detail=str(e)
                ),
            )
