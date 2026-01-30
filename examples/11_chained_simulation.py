"""Example of Chained Simulation in Multi-Step Plans.

This example demonstrates how to:
1. Execute a multi-step plan in simulation mode.
2. Verify that steps are 'chained' in memory (e.g., Step 2 sees the state produced by Step 1).
3. Ensure no data is committed to the repository.
"""

from gradio_chat_agent.execution.engine import ExecutionEngine
from gradio_chat_agent.models.enums import ExecutionMode, IntentType
from gradio_chat_agent.models.intent import ChatIntent
from gradio_chat_agent.models.plan import ExecutionPlan
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
    project_id = "chained-sim-demo"

    registry.register_component(counter_component)
    registry.register_action(set_action, set_handler)
    registry.register_action(increment_action, increment_handler)

    # 2. Construct a multi-step plan
    print("--- Constructing Plan ---")
    step_1 = ChatIntent(
        type=IntentType.ACTION_CALL,
        request_id="step-1",
        action_id="demo.counter.set",
        inputs={"value": 50},
        execution_mode=ExecutionMode.AUTONOMOUS,
    )

    step_2 = ChatIntent(
        type=IntentType.ACTION_CALL,
        request_id="step-2",
        action_id="demo.counter.increment",
        inputs={"amount": 25},
        execution_mode=ExecutionMode.AUTONOMOUS,
    )

    plan = ExecutionPlan(plan_id="plan-1", steps=[step_1, step_2])

    # 3. Run Simulated Plan
    print("\n--- Running Chained Simulation ---")
    # Note: simulate=True
    results = engine.execute_plan(project_id, plan, simulate=True)

    for i, res in enumerate(results):
        print(f"Step {i + 1} ({res.action_id}) Status: {res.status}")
        print(f"  Simulated: {res.simulated}")
        print(f"  Message: {res.message}")

    # Check the simulated state of the last result
    # (Internal attribute used for chaining)
    if hasattr(results[-1], "_simulated_state"):
        assert results[-1]._simulated_state is not None
        final_val = results[-1]._simulated_state["demo.counter"]["value"]
        print(f"\nFinal Simulated Value: {final_val} (Expected: 75)")

    # 4. Verify Repository is Still Empty
    print("\n--- Verifying Repository ---")
    latest = repository.get_latest_snapshot(project_id)
    print(f"Snapshot exists in DB? {latest is not None}")

    # Run for real to see the difference
    print("\n--- Executing Real Plan ---")
    engine.execute_plan(project_id, plan, simulate=False)
    latest_real = repository.get_latest_snapshot(project_id)
    assert latest_real is not None
    print(
        f"Real Value in DB: {latest_real.components['demo.counter']['value']}"
    )


if __name__ == "__main__":
    run_example()
