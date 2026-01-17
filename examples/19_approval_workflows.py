"""Example of Approval Workflows and Pending Status.

This example demonstrates how to:
1. Define approval rules based on action cost and user roles.
2. Observe actions entering the 'PENDING_APPROVAL' status.
3. Successfully execute a previously pending action after obtaining approval.
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
    project_id = "approval-demo"
    repository.create_project(project_id, "Approval Demo")

    # 1. Define an expensive action
    expensive_action = ActionDeclaration(
        action_id="demo.heavy.operation",
        title="Expensive Operation",
        description="Costs 50 units.",
        targets=["demo"],
        input_schema={},
        permission=ActionPermission(
            confirmation_required=False,
            risk=ActionRisk.MEDIUM,
            visibility=ActionVisibility.USER,
        ),
        cost=50.0,
    )
    registry.register_action(
        expensive_action, lambda i, s: ({}, [], "Heavy work complete")
    )

    # 2. Setup Approval Policy
    # Any action costing 20 or more requires 'admin' role
    print("--- Policy: Actions >= 20 units require admin approval ---")
    policy = {"approvals": [{"min_cost": 20.0, "required_role": "admin"}]}
    repository.set_project_limits(project_id, policy)

    # 3. Scenario: Operator tries to execute the expensive action
    print("\n--- Scenario 1: Operator attempts expensive action ---")
    intent = ChatIntent(
        type=IntentType.ACTION_CALL,
        request_id="req-123",
        action_id="demo.heavy.operation",
        inputs={},
    )
    res1 = engine.execute_intent(project_id, intent, user_roles=["operator"])

    print(f"Result Status: {res1.status}")
    print(f"Result Message: {res1.message}")

    # 4. Scenario: Admin approves the action
    print("\n--- Scenario 2: Admin executes the action (or confirms it) ---")
    # In the UI, the admin would see the request and click 'Approve'
    # which re-submits the intent with confirmed=True
    intent.confirmed = True
    res2 = engine.execute_intent(project_id, intent, user_roles=["admin"])

    print(f"Result Status: {res2.status}")
    print(f"Result Message: {res2.message}")


if __name__ == "__main__":
    run_example()
