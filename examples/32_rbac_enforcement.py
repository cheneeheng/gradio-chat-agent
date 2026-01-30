"""Example of strict RBAC Role Enforcement in the Execution Engine.

This example demonstrates:
1. Rejection of all actions for 'viewer' role.
2. Rejection of high-risk actions for 'operator' role.
3. Successful execution of all risk levels for 'admin' role.
"""

from gradio_chat_agent.execution.engine import ExecutionEngine
from gradio_chat_agent.models.action import (
    ActionDeclaration,
    ActionPermission,
)
from gradio_chat_agent.models.enums import (
    ActionRisk,
    ActionVisibility,
    IntentType,
)
from gradio_chat_agent.models.intent import ChatIntent
from gradio_chat_agent.persistence.in_memory import InMemoryStateRepository
from gradio_chat_agent.registry.in_memory import InMemoryRegistry


def run_example():
    registry = InMemoryRegistry()
    repository = InMemoryStateRepository()
    engine = ExecutionEngine(registry, repository)
    project_id = "rbac-demo"

    # Register actions with different risk levels
    low_risk_action = ActionDeclaration(
        action_id="demo.low",
        title="Low Risk",
        description="Safe action.",
        targets=["demo"],
        input_schema={},
        permission=ActionPermission(
            confirmation_required=False,
            risk=ActionRisk.LOW,
            visibility=ActionVisibility.USER,
        ),
    )
    high_risk_action = ActionDeclaration(
        action_id="demo.high",
        title="High Risk",
        description="Dangerous action.",
        targets=["demo"],
        input_schema={},
        permission=ActionPermission(
            confirmation_required=True,
            risk=ActionRisk.HIGH,
            visibility=ActionVisibility.USER,
        ),
    )

    registry.register_action(low_risk_action, lambda i, s: ({}, [], "Low Done"))
    registry.register_action(high_risk_action, lambda i, s: ({}, [], "High Done"))

    print("--- Scenario 1: Viewer tries to execute LOW risk ---")
    intent_low = ChatIntent(type=IntentType.ACTION_CALL, request_id="r1", action_id="demo.low")
    res = engine.execute_intent(project_id, intent_low, user_roles=["viewer"])
    print(f"Result (Viewer, Low): {res.status} - {res.message}")

    print("\n--- Scenario 2: Operator tries to execute HIGH risk ---")
    intent_high = ChatIntent(type=IntentType.ACTION_CALL, request_id="r2", action_id="demo.high", confirmed=True)
    res = engine.execute_intent(project_id, intent_high, user_roles=["operator"])
    print(f"Result (Operator, High): {res.status} - {res.message}")

    print("\n--- Scenario 3: Operator tries to execute LOW risk ---")
    res = engine.execute_intent(project_id, intent_low, user_roles=["operator"])
    print(f"Result (Operator, Low): {res.status} - {res.message}")

    print("\n--- Scenario 4: Admin tries to execute HIGH risk ---")
    res = engine.execute_intent(project_id, intent_high, user_roles=["admin"])
    print(f"Result (Admin, High): {res.status} - {res.message}")


if __name__ == "__main__":
    run_example()
