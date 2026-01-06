def adapt_daily_budget(
    repo,
    project_id: int,
    min_budget: int,
    max_budget: int,
):
    history = repo.get_daily_usage_history(project_id, days=7)
    if len(history) < 3:
        return

    avg = sum(history) / len(history)

    new_budget = int(avg * 1.2)  # 20% headroom
    new_budget = max(min_budget, min(max_budget, new_budget))

    repo.update_project_budget(project_id, new_budget)
