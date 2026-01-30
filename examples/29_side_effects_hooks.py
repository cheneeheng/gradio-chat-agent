"""Example of using Post-Execution Hooks for Side Effects.

This example demonstrates how to:
1. Register a post-execution hook in the ExecutionEngine.
2. Observe the hook being triggered after a successful action.
3. Verify that hooks are NOT triggered during simulation.
"""

from gradio_chat_agent.execution.engine import ExecutionEngine
from gradio_chat_agent.models.enums import IntentType
from gradio_chat_agent.models.intent import ChatIntent
from gradio_chat_agent.persistence.in_memory import InMemoryStateRepository
from gradio_chat_agent.registry.demo_actions import (
    counter_component,
    set_action,
    set_handler,
)
from gradio_chat_agent.registry.in_memory import InMemoryRegistry


def run_example():
    # 1. Setup system
    registry = InMemoryRegistry()
    repository = InMemoryStateRepository()
    engine = ExecutionEngine(registry, repository)
    project_id = "hooks-demo"

    registry.register_component(counter_component)
    registry.register_action(set_action, set_handler)

    # 2. Define a side effect hook
    triggered_actions = []

    def my_side_effect(pid: str, result):
        print(f"DEBUG: Side effect triggered for project {pid}, action {result.action_id}")
        triggered_actions.append(result.action_id)

    # 3. Register the hook
    engine.add_post_execution_hook(my_side_effect)

    print("--- Scenario 1: Real Execution ---")
    intent = ChatIntent(
        type=IntentType.ACTION_CALL,
        request_id="req-1",
        action_id="demo.counter.set",
        inputs={"value": 10},
    )
    res1 = engine.execute_intent(project_id, intent)
    print(f"Execution Status: {res1.status}")
    print(f"Triggered Actions: {triggered_actions}")

    print("\n--- Scenario 2: Simulation (Should NOT trigger hooks) ---")
    intent_sim = ChatIntent(
        type=IntentType.ACTION_CALL,
        request_id="req-sim",
        action_id="demo.counter.set",
        inputs={"value": 20},
    )
    res_sim = engine.execute_intent(project_id, intent_sim, simulate=True)
    print(f"Simulation Status: {res_sim.status}")
    print(f"Triggered Actions: {triggered_actions} (Expected: unchanged)")

    print("\n--- Scenario 3: Failed Execution (Should NOT trigger hooks) ---")
    intent_fail = ChatIntent(
        type=IntentType.ACTION_CALL,
        request_id="req-fail",
        action_id="missing.action",
    )
    res_fail = engine.execute_intent(project_id, intent_fail)
    print(f"Failure Status: {res_fail.status}")
    print(f"Triggered Actions: {triggered_actions} (Expected: unchanged)")


if __name__ == "__main__":
    run_example()
