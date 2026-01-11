"""Example of Multi-Step Execution Plans.

This example demonstrates how to:
1. Construct an `ExecutionPlan` with multiple dependent steps.
2. Execute the plan via the engine.
3. Handle partial failures (though this example shows success).
"""

import uuid

from gradio_chat_agent.execution.engine import ExecutionEngine
from gradio_chat_agent.models.enums import (
    IntentType,
)
from gradio_chat_agent.models.intent import ChatIntent
from gradio_chat_agent.models.plan import ExecutionPlan
from gradio_chat_agent.models.state_snapshot import StateSnapshot
from gradio_chat_agent.persistence.in_memory import InMemoryStateRepository
from gradio_chat_agent.registry.demo_actions import (
    counter_component,
    increment_action,
    increment_handler,
    set_action,
    set_handler,
)
from gradio_chat_agent.registry.in_memory import InMemoryRegistry


def run_example():
    # 1. Initialize
    registry = InMemoryRegistry()
    repository = InMemoryStateRepository()
    engine = ExecutionEngine(registry, repository)
    project_id = "planning-demo"

    # Register actions
    registry.register_component(counter_component)
    registry.register_action(set_action, set_handler)
    registry.register_action(increment_action, increment_handler)

    # Initial state
    repository.save_snapshot(
        project_id,
        StateSnapshot(
            snapshot_id="init", components={"demo.counter": {"value": 0}}
        ),
    )

    # 2. Construct a Plan
    # Goal: Set counter to 10, then increment by 5
    print("--- Constructing Execution Plan ---")

    step_1 = ChatIntent(
        type=IntentType.ACTION_CALL,
        request_id="step-1",
        action_id="demo.counter.set",
        inputs={"value": 10},
    )

    step_2 = ChatIntent(
        type=IntentType.ACTION_CALL,
        request_id="step-2",
        action_id="demo.counter.increment",
        inputs={"amount": 5},
    )

    plan = ExecutionPlan(
        plan_id=f"plan-{uuid.uuid4().hex[:8]}", steps=[step_1, step_2]
    )

    print(f"Plan ID: {plan.plan_id}")
    print(f"Steps: {len(plan.steps)}")

    # 3. Execute Plan
    print("\n--- Executing Plan ---")
    results = engine.execute_plan(project_id, plan, user_roles=["admin"])

    # 4. Verify Results
    print("\n--- Execution Results ---")
    for res in results:
        status_icon = "✅" if res.status == "success" else "❌"
        print(f"{status_icon} Action: {res.action_id} -> {res.message}")

    # Check final state
    snapshot = repository.get_latest_snapshot(project_id)
    assert snapshot is not None
    final_val = snapshot.components["demo.counter"]["value"]
    print(f"\nFinal Counter Value: {final_val} (Expected: 15)")


if __name__ == "__main__":
    run_example()
