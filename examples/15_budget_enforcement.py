"""Example of Action Budgets and Daily Limit Enforcement.

This example demonstrates how to:
1. Define custom costs for different actions.
2. Set a daily budget limit for a project.
3. Observe the engine rejecting actions once the budget is exhausted.
4. Verify that simulated executions do not consume budget.
"""

import uuid

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
    # 1. Setup system components
    registry = InMemoryRegistry()
    repository = InMemoryStateRepository()
    engine = ExecutionEngine(registry, repository)
    project_id = "budget-demo-project"
    repository.create_project(project_id, "Budget Demo")

    # 2. Register actions with different costs
    # Default cost is 1.0, but we can override it
    cheap_action = ActionDeclaration(
        action_id="demo.cheap",
        title="Cheap Action",
        description="A low-cost operation.",
        targets=["demo"],
        input_schema={},
        permission=ActionPermission(
            confirmation_required=False,
            risk=ActionRisk.LOW,
            visibility=ActionVisibility.USER,
        ),
        cost=1.0,  # Explicitly setting the default
    )

    expensive_action = ActionDeclaration(
        action_id="demo.expensive",
        title="Expensive Action",
        description="A high-cost operation.",
        targets=["demo"],
        input_schema={},
        permission=ActionPermission(
            confirmation_required=False,
            risk=ActionRisk.LOW,
            visibility=ActionVisibility.USER,
        ),
        cost=10.0,  # This action is 10x more expensive
    )

    registry.register_action(cheap_action, lambda i, s: ({}, [], "Cheap Done"))
    registry.register_action(
        expensive_action, lambda i, s: ({}, [], "Expensive Done")
    )

    # 3. Set project budget policy
    # Daily budget of 15 credits
    print(f"Setting daily budget for project '{project_id}' to 15.0 units.")
    policy = {"limits": {"budget": {"daily": 15.0}}}
    repository.set_project_limits(project_id, policy)

    # 4. Execute actions
    print("\n--- Execution 1: Expensive Action (Cost: 10.0) ---")
    intent1 = ChatIntent(
        type=IntentType.ACTION_CALL,
        request_id=str(uuid.uuid4()),
        action_id="demo.expensive",
        inputs={},
    )
    res1 = engine.execute_intent(project_id, intent1)
    print(
        f"Result: {res1.status} (Usage: {repository.get_daily_budget_usage(project_id)}/15.0)"
    )

    print("\n--- Execution 2: Cheap Action (Cost: 1.0) ---")
    intent2 = ChatIntent(
        type=IntentType.ACTION_CALL,
        request_id=str(uuid.uuid4()),
        action_id="demo.cheap",
        inputs={},
    )
    res2 = engine.execute_intent(project_id, intent2)
    print(
        f"Result: {res2.status} (Usage: {repository.get_daily_budget_usage(project_id)}/15.0)"
    )

    print("\n--- Execution 3: Simulation (Cost: 10.0) ---")
    # Simulations should NOT check or consume budget
    res3 = engine.execute_intent(project_id, intent1, simulate=True)
    print(f"Result: {res3.status} (Simulated: {res3.simulated})")
    print(
        f"Usage after simulation: {repository.get_daily_budget_usage(project_id)}/15.0"
    )

    print("\n--- Execution 4: Exceeding Budget (Attempting 10.0 more) ---")
    # Current usage: 11.0. Adding 10.0 would make it 21.0 > 15.0
    res4 = engine.execute_intent(project_id, intent1)
    print(
        f"Result: {res4.status} (Error Code: {res4.error.code if res4.error else 'None'})"
    )
    print(f"Final Usage: {repository.get_daily_budget_usage(project_id)}/15.0")


if __name__ == "__main__":
    run_example()
