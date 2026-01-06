from datetime import datetime, timedelta, timezone

from gradio_chat_agent.persistence.repo import StateRepository


def forecast_budget_exhaustion(
    repo: StateRepository,
    project_id: int,
    daily_budget: int,
    lookback_hours: int = 6,
) -> dict:
    now = datetime.now(timezone.utc)
    since = now - timedelta(hours=lookback_hours)

    executions = repo.list_executions_since(project_id, since)
    if not executions:
        return {"status": "insufficient_data"}

    total_cost = sum(
        e.metadata.get("limits", {}).get("cost", 0) for e in executions
    )
    hours = lookback_hours

    burn_rate_per_hour = total_cost / hours
    if burn_rate_per_hour <= 0:
        return {"status": "no_burn"}

    hours_remaining = (daily_budget - total_cost) / burn_rate_per_hour

    return {
        "status": "ok",
        "burn_rate_per_hour": round(burn_rate_per_hour, 2),
        "estimated_exhaustion_at": (
            now + timedelta(hours=hours_remaining)
        ).isoformat(),
    }
