"""Example of Simulation (Dry-Run) Mode.

This example demonstrates how to:
1. Use the simulation flag in the execution engine.
2. Preview the state impact of an action without committing it to the database.
3. Verify that the repository state remains unchanged after a simulation.
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
    # 1. Initialize
    registry = InMemoryRegistry()
    repository = InMemoryStateRepository()
    engine = ExecutionEngine(registry, repository)
    project_id = "simulation-demo"

    registry.register_component(counter_component)
    registry.register_action(set_action, set_handler)

    print("--- Initial State ---")
    # Initial state: counter = 0
    snapshot = repository.get_latest_snapshot(project_id)
    print(f"Counter exists: {snapshot is not None}")

    # 2. Execute a Simulated Intent
    print("\n--- Executing Simulated Action ---")
    intent = ChatIntent(
        type=IntentType.ACTION_CALL,
        request_id="sim-req-1",
        action_id="demo.counter.set",
        inputs={"value": 100},
    )

    # Note the 'simulate=True' flag
    res = engine.execute_intent(project_id, intent, simulate=True)

    print(f"Status: {res.status}")
    print(f"Is Simulated: {res.simulated}")
    print(f"Message: {res.message}")
    print(f"Proposed Diff: {res.state_diff}")

    # 3. Verify Repository State
    print("\n--- Verifying Database Integrity ---")
    latest = repository.get_latest_snapshot(project_id)
    print(f"Latest Snapshot exists in DB: {latest is not None}")

    history = repository.get_execution_history(project_id)
    print(f"Audit Log Entries: {len(history)}")

    # 4. Execute for Real
    print("\n--- Executing Real Action ---")
    res_real = engine.execute_intent(project_id, intent, simulate=False)
    print(f"Real Execution Status: {res_real.status}")
    print(f"Is Simulated: {res_real.simulated}")

    latest_after = repository.get_latest_snapshot(project_id)
    assert latest_after is not None
    print(
        f"Counter Value in DB: {latest_after.components['demo.counter']['value']}"
    )


if __name__ == "__main__":
    run_example()
