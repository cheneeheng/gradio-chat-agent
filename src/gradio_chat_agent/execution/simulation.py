from dataclasses import dataclass

from gradio_chat_agent.execution.costs import compute_action_cost


@dataclass
class SimulationStep:
    action_id: str
    cost: int
    would_exceed_budget: bool
    would_exceed_action_budget: bool


@dataclass
class SimulationResult:
    total_cost: int
    steps: list[SimulationStep]
    would_exceed_project_budget: bool


def simulate_plan_execution(repo, project_id: int, plan) -> SimulationResult:
    limits = repo.get_project_limits(project_id)
    project_budget = limits.daily_budget if limits else None
    used = limits.budget_used_today if limits else 0

    total_cost = 0
    steps: list[SimulationStep] = []

    for step in plan.steps:
        action = repo.get_action(step.action_id)
        cost = compute_action_cost(action)
        total_cost += cost

        step_exceeds_project = (
            project_budget is not None and used + total_cost > project_budget
        )

        step_exceeds_action = repo.action_budget_exceeded(
            project_id, step.action_id, cost
        )

        steps.append(
            SimulationStep(
                action_id=step.action_id,
                cost=cost,
                would_exceed_budget=step_exceeds_project,
                would_exceed_action_budget=step_exceeds_action,
            )
        )

    return SimulationResult(
        total_cost=total_cost,
        steps=steps,
        would_exceed_project_budget=(
            project_budget is not None and used + total_cost > project_budget
        ),
    )
