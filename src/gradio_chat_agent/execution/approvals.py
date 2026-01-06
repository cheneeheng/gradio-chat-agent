def requires_human_approval(
    repo, project_id: int, cost: int, user_roles: set[str]
) -> bool:
    rules = repo.get_approval_rules(project_id)
    for r in rules:
        if (
            r.enabled
            and cost >= r.min_cost
            and r.required_role not in user_roles
        ):
            return True
    return False
