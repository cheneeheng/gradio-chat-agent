RISK_MULTIPLIER = {
    "low": 1,
    "medium": 5,
    "high": 20,
}


def compute_action_cost(action) -> int:
    multiplier = RISK_MULTIPLIER.get(action.permission.risk, 1)
    return action.permission.base_cost * multiplier
