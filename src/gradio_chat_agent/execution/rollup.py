def org_usage_rollup(repo, user_id: int) -> dict:
    projects = repo.list_projects_for_user(user_id)

    summary = {}
    for pid, name, role in projects:
        limits = repo.get_project_limits(pid)
        summary[name] = {
            "budget_used": limits.budget_used_today if limits else 0,
            "budget_total": limits.daily_budget if limits else None,
            "executions_today": repo.count_executions_today(pid),
        }

    return summary
