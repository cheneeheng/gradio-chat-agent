from __future__ import annotations

from ..execution.plan import ExecutionPlan
from ..models.action import ActionDeclaration


def format_plan_markdown_with_warnings(
    plan: ExecutionPlan,
    *,
    actions: dict[str, ActionDeclaration],
    user_roles: set[str],
) -> str:
    lines: list[str] = [f"### Proposed plan: `{plan.plan_id}`"]

    warnings: list[str] = []
    for i, s in enumerate(plan.steps):
        lines.append(f"- **Step {i}**: `{s.action_id}` inputs={s.inputs}")

        a = actions.get(s.action_id)
        if not a:
            warnings.append(
                f"- Step {i}: unknown action `{s.action_id}` (will be rejected)."
            )
            continue

        req = set(a.permission.required_roles or set())
        if req and not (req & user_roles) and "admin" not in user_roles:
            warnings.append(
                f"- Step {i}: requires roles {sorted(req)}, but you have {sorted(user_roles)} (will be rejected)."
            )

        if a.permission.confirmation_required or a.permission.risk == "high":
            warnings.append(
                f"- Step {i}: requires explicit confirmation (confirmation_required/risk=high)."
            )

    if warnings:
        lines.append("")
        lines.append("### Warnings")
        lines.extend(warnings)

    lines.append("")
    lines.append("Approve to execute, or reject to ask for clarification.")
    return "\n".join(lines)


def format_plan_simulation(sim: SimulationResult) -> str:
    lines = ["### Budget simulation"]

    for s in sim.steps:
        warn = []
        if s.would_exceed_budget:
            warn.append("⚠ project budget")
        if s.would_exceed_action_budget:
            warn.append("⚠ action budget")

        suffix = f" ({', '.join(warn)})" if warn else ""
        lines.append(f"- `{s.action_id}` cost={s.cost}{suffix}")

    lines.append("")
    lines.append(f"**Total cost:** {sim.total_cost}")

    if sim.would_exceed_project_budget:
        lines.append("❌ This plan would exceed the project budget.")

    return "\n".join(lines)
