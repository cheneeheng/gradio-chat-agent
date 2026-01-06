from datetime import datetime, timedelta, timezone

from gradio_chat_agent.persistence.repo import StateRepository, ProjectIdentity
from gradio_chat_agent.persistence.models import ProjectLimitsRow


class LimitViolation(Exception):
    def __init__(self, code: str, detail: str):
        self.code = code
        self.detail = detail
        super().__init__(detail)


def enforce_action_budget(
    repo, project_id: int, action_id: str, cost: int, now: datetime
):
    budget = repo.get_action_budget(project_id, action_id)
    if not budget or budget.daily_budget is None:
        return

    if budget.budget_reset_at is None or now >= budget.budget_reset_at:
        budget.budget_used_today = 0
        budget.budget_reset_at = now.replace(
            hour=0, minute=0, second=0
        ) + timedelta(days=1)

    if budget.budget_used_today + cost > budget.daily_budget:
        raise LimitViolation(
            "budget.action.exceeded",
            f"Action `{action_id}` exceeded daily budget ({budget.budget_used_today}/{budget.daily_budget})",
        )

    budget.budget_used_today += cost
    repo.save_action_budget(budget)
