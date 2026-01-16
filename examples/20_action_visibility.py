"""Example of Action Visibility Filtering.

This example demonstrates how:
1. Actions can be marked with 'user' or 'developer' visibility.
2. The registry filters these actions based on the user's role in the project.
3. Developer actions are hidden from standard users (viewers/operators).
"""

from gradio_chat_agent.execution.engine import ExecutionEngine
from gradio_chat_agent.api.endpoints import ApiEndpoints
from gradio_chat_agent.models.action import (
    ActionDeclaration,
    ActionPermission,
)
from gradio_chat_agent.models.enums import (
    ActionRisk,
    ActionVisibility,
)
from gradio_chat_agent.persistence.in_memory import InMemoryStateRepository
from gradio_chat_agent.registry.in_memory import InMemoryRegistry

def run_example():
    registry = InMemoryRegistry()
    repository = InMemoryStateRepository()
    engine = ExecutionEngine(registry, repository)
    api = ApiEndpoints(engine)
    
    project_id = "visibility-demo"
    repository.create_project(project_id, "Visibility Demo")

    # 1. Register a standard USER action
    user_action = ActionDeclaration(
        action_id="demo.hello",
        title="Say Hello",
        description="A standard user action.",
        targets=["demo"],
        input_schema={},
        permission=ActionPermission(
            confirmation_required=False,
            risk=ActionRisk.LOW,
            visibility=ActionVisibility.USER,
        )
    )
    registry.register_action(user_action, lambda i, s: ({}, [], "Hello"))

    # 2. Register a DEVELOPER action
    dev_action = ActionDeclaration(
        action_id="demo.debug.reset",
        title="Debug Reset",
        description="A sensitive developer-only action.",
        targets=["demo"],
        input_schema={},
        permission=ActionPermission(
            confirmation_required=False,
            risk=ActionRisk.HIGH,
            visibility=ActionVisibility.DEVELOPER,
        )
    )
    registry.register_action(dev_action, lambda i, s: ({}, [], "Debug complete"))

    # 3. Setup Project Members
    repository.add_project_member(project_id, "alice_admin", "admin")
    repository.add_project_member(project_id, "bob_operator", "operator")

    print("--- Scenario 1: Admin User (Alice) ---")
    reg_admin = api.get_registry(project_id, user_id="alice_admin")
    admin_actions = [a["action_id"] for a in reg_admin["actions"]]
    print(f"Visible Actions for Admin: {admin_actions}")
    assert "demo.debug.reset" in admin_actions

    print("\n--- Scenario 2: Standard User (Bob) ---")
    reg_user = api.get_registry(project_id, user_id="bob_operator")
    user_actions = [a["action_id"] for a in reg_user["actions"]]
    print(f"Visible Actions for Operator: {user_actions}")
    assert "demo.debug.reset" not in user_actions
    assert "demo.hello" in user_actions

    print("\n--- Scenario 3: Anonymous/Viewer ---")
    reg_anon = api.get_registry(project_id, user_id="unknown")
    anon_actions = [a["action_id"] for a in reg_anon["actions"]]
    print(f"Visible Actions for Anonymous: {anon_actions}")
    assert "demo.debug.reset" not in anon_actions

if __name__ == "__main__":
    run_example()
