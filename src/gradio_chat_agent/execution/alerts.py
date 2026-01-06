import requests


def evaluate_budget_alerts(repo, project_id: int):
    limits = repo.get_project_limits(project_id)
    if not limits or not limits.daily_budget:
        return

    used = limits.budget_used_today
    percent = int((used / limits.daily_budget) * 100)

    rules = repo.get_alert_rules(project_id)
    for rule in rules:
        if rule.enabled and percent >= rule.threshold_percent:
            requests.post(
                rule.webhook_url,
                json={
                    "project_id": project_id,
                    "budget_used": used,
                    "budget_total": limits.daily_budget,
                    "percent": percent,
                },
                timeout=3,
            )
