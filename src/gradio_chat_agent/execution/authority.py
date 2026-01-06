# Canonical role ordering (lowest → highest authority)
ROLE_ORDER = ["viewer", "operator", "admin"]

ROLE_RANK = {r: i for i, r in enumerate(ROLE_ORDER)}


def normalize_roles(roles: set[str]) -> set[str]:
    """
    Ensures role set is sane and ordered.
    """
    if not roles:
        return {"viewer"}
    return set(roles)


def has_minimum_role(user_roles: set[str], required_roles: set[str]) -> bool:
    """
    True if user has at least one required role.
    """
    if not required_roles:
        return True
    return bool(user_roles & required_roles)


def is_viewer_only(user_roles: set[str]) -> bool:
    return user_roles == {"viewer"}
