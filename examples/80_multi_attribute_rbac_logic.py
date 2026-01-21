"""Example of Multi-Attribute Dynamic RBAC.

This example demonstrates how to:
1. Define role mappings using complex Python expressions.
2. Check multiple user attributes simultaneously (e.g., email domain AND organization).
3. Verify the engine resolves these roles correctly during intent execution.
"""

from gradio_chat_agent.execution.engine import ExecutionEngine
from gradio_chat_agent.persistence.in_memory import InMemoryStateRepository
from gradio_chat_agent.registry.in_memory import InMemoryRegistry

def run_example():
    registry = InMemoryRegistry()
    repository = InMemoryStateRepository()
    engine = ExecutionEngine(registry, repository)
    project_id = "multi-attr-rbac"
    repository.create_project(project_id, "Security Demo")

    # 1. Define Policy with Complex Conditions
    policy = {
        "role_mappings": [
            {
                "role": "admin", 
                "condition": "user.email.endswith('@it.corp') and user.organization_id == 'infrastructure'"
            },
            {
                "role": "operator",
                "condition": "user.organization_id in ['support', 'operations']"
            }
        ]
    }
    repository.set_project_limits(project_id, policy)

    # 2. Create Users with Varied Attributes
    # Alice: Admin (Matches both)
    repository.create_user("alice", "h", email="alice@it.corp", organization_id="infrastructure")
    # Bob: Operator (Matches list)
    repository.create_user("bob", "h", email="bob@it.corp", organization_id="support")
    # Charlie: Viewer (Matches neither)
    repository.create_user("charlie", "h", email="charlie@hr.corp", organization_id="hr")

    # 3. Test Role Resolution
    print("--- Role Resolution Test ---")
    users = ["alice", "bob", "charlie"]
    for uid in users:
        roles = engine.resolve_user_roles(project_id, uid)
        user = repository.get_user(uid)
        print(f"User: {uid:10} | Org: {user['organization_id']:15} | Resolved Roles: {roles}")

    # 4. Verify resolving logic
    assert "admin" in engine.resolve_user_roles(project_id, "alice")
    assert "operator" in engine.resolve_user_roles(project_id, "bob")
    assert "viewer" in engine.resolve_user_roles(project_id, "charlie")
    print("\nSUCCESS: Multi-attribute RBAC logic correctly enforced.")

if __name__ == "__main__":
    run_example()
