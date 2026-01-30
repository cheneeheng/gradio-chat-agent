"""Example of State Reversion (Time Travel).

This example demonstrates how to:
1. Create a snapshot of the current state.
2. Perform actions that modify the state.
3. Revert the project back to the original snapshot.
4. Verify the audit log records the reversion.
"""

from gradio_chat_agent.execution.engine import ExecutionEngine
from gradio_chat_agent.models.enums import IntentType
from gradio_chat_agent.models.intent import ChatIntent
from gradio_chat_agent.models.state_snapshot import StateSnapshot
from gradio_chat_agent.persistence.in_memory import InMemoryStateRepository
from gradio_chat_agent.registry.demo_actions import (
    counter_component,
    set_action,
    set_handler,
)
from gradio_chat_agent.registry.in_memory import InMemoryRegistry


def run_example():
    # 1. Initialize
    registry = InMemoryRegistry()
    repository = InMemoryStateRepository()
    engine = ExecutionEngine(registry, repository)
    project_id = "revert-demo"

    registry.register_component(counter_component)
    registry.register_action(set_action, set_handler)

    # 2. Establish Baseline State
    print("--- Establishing Baseline State ---")
    baseline_id = "snapshot-baseline"
    baseline_snapshot = StateSnapshot(
        snapshot_id=baseline_id, components={"demo.counter": {"value": 100}}
    )
    repository.save_snapshot(project_id, baseline_snapshot)
    print(f"Baseline Snapshot ID: {baseline_id} (Value: 100)")

    # 3. Mutate State
    print("\n--- Mutating State ---")
    intent = ChatIntent(
        type=IntentType.ACTION_CALL,
        request_id="req-1",
        action_id="demo.counter.set",
        inputs={"value": 999},
    )
    res = engine.execute_intent(project_id, intent)
    print(f"Executed Action: {res.message}")

    current_snap = repository.get_latest_snapshot(project_id)
    assert current_snap is not None
    print(
        f"Current State Value: {current_snap.components['demo.counter']['value']}"
    )

    # 4. Revert
    print(f"\n--- Reverting to {baseline_id} ---")
    revert_res = engine.revert_to_snapshot(project_id, baseline_id)

    print(f"Revert Status: {revert_res.status}")
    print(f"Message: {revert_res.message}")

    # 5. Verify
    print("\n--- Verification ---")
    final_snap = repository.get_latest_snapshot(project_id)
    assert final_snap is not None
    final_val = final_snap.components["demo.counter"]["value"]
    print(f"Restored Value: {final_val} (Expected: 100)")

    print("\n--- Audit Log ---")
    history = repository.get_execution_history(project_id)
    for entry in history:
        print(f"[{entry.timestamp}] {entry.action_id} -> {entry.status}")


if __name__ == "__main__":
    run_example()
