"""Example of Dynamic RBAC Role Mapping.

This example demonstrates how to:
1. Define dynamic role mapping rules in the project policy.
2. Resolve user roles based on user attributes (e.g., email domain).
3. Observe how users without explicit membership get roles assigned dynamically.
"""

import uuid
from gradio_chat_agent.execution.engine import ExecutionEngine
from gradio_chat_agent.persistence.in_memory import InMemoryStateRepository
from gradio_chat_agent.registry.in_memory import InMemoryRegistry
from gradio_chat_agent.models.action import ActionDeclaration, ActionPermission
from gradio_chat_agent.models.enums import ActionRisk, ActionVisibility

def run_example():
    # 1. Setup system
    registry = InMemoryRegistry()
    repository = InMemoryStateRepository()
    engine = ExecutionEngine(registry, repository)
    project_id = "rbac-mapping-demo"
    repository.create_project(project_id, "RBAC Mapping Demo")

    # 2. Define Policy with Role Mappings
    # Rules:
    # - Users with @admin.corp email get 'admin' role.
    # - Users with @staff.corp email get 'operator' role.
    policy = {
        "role_mappings": [
            {"role": "admin", "condition": "user.email.endswith('@admin.corp')"},
            {"role": "operator", "condition": "user.email.endswith('@staff.corp')"}
        ]
    }
    repository.set_project_limits(project_id, policy)

    # 3. Create Users
    # Alice: Admin by email
    repository.create_user("alice", "hash", full_name="Alice Admin", email="alice@admin.corp")
    # Bob: Operator by email
    repository.create_user("bob", "hash", full_name="Bob Staff", email="bob@staff.corp")
    # Charlie: Viewer (default)
    repository.create_user("charlie", "hash", full_name="Charlie Guest", email="charlie@gmail.com")
    # Dave: Admin by explicit membership (overrides rules)
    repository.create_user("dave", "hash", full_name="Dave Boss", email="dave@gmail.com")
    repository.add_project_member(project_id, "dave", "admin")

    print(f"--- Role Resolution for Project: {project_id} ---")

    users = ["alice", "bob", "charlie", "dave", "unknown_user"]
    for uid in users:
        roles = engine.resolve_user_roles(project_id, uid)
        print(f"User: {uid:15} -> Resolved Roles: {roles}")

    # 4. Verify Execution based on resolved roles
    registry.register_action(
        ActionDeclaration(
            action_id="demo.restricted",
            title="Restricted Action",
            description="Requires Admin",
            targets=["t"],
            input_schema={},
            permission=ActionPermission(confirmation_required=False, risk=ActionRisk.HIGH, visibility=ActionVisibility.USER)
        ),
        handler=lambda i, s: ({}, [], "Success")
    )

    from gradio_chat_agent.models.intent import ChatIntent
    from gradio_chat_agent.models.enums import IntentType

    intent = ChatIntent(type=IntentType.ACTION_CALL, request_id="r1", action_id="demo.restricted", confirmed=True)

    print("\n--- Execution Test ---")
    # Alice should succeed because she's resolved as admin
    res_alice = engine.execute_intent(project_id, intent, user_id="alice", user_roles=engine.resolve_user_roles(project_id, "alice"))
    print(f"Alice execution: {res_alice.status}")

    # Bob should fail because he's operator (can't do high risk)
    res_bob = engine.execute_intent(project_id, intent, user_id="bob", user_roles=engine.resolve_user_roles(project_id, "bob"))
    print(f"Bob execution:   {res_bob.status} ({res_bob.message})")

if __name__ == "__main__":
    run_example()
