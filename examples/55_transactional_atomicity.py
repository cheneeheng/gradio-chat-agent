"""Example of Transactional Atomicity.

This example demonstrates how the system ensures that state snapshots and
execution results are persisted atomically in a single transaction.
"""

import uuid
from datetime import datetime
from gradio_chat_agent.execution.engine import ExecutionEngine
from gradio_chat_agent.models.enums import IntentType, ExecutionStatus
from gradio_chat_agent.models.intent import ChatIntent
from gradio_chat_agent.models.state_snapshot import StateSnapshot
from gradio_chat_agent.persistence.sql_repository import SQLStateRepository
from gradio_chat_agent.registry.demo_actions import (
    counter_component,
    set_action,
    set_handler,
)
from gradio_chat_agent.registry.in_memory import InMemoryRegistry


def run_example():
    # 1. Setup system with SQL repository (in-memory SQLite)
    db_url = "sqlite:///:memory:"
    print(f"Initializing SQL Repository with {db_url}...")
    repository = SQLStateRepository(db_url)
    registry = InMemoryRegistry()
    engine = ExecutionEngine(registry, repository)
    project_id = "transaction-demo"

    # 2. Register demo actions
    registry.register_component(counter_component)
    registry.register_action(set_action, set_handler)

    print("\n--- Executing Action with Atomic Persistence ---")
    
    # 3. Execute an action
    intent = ChatIntent(
        type=IntentType.ACTION_CALL,
        request_id=str(uuid.uuid4()),
        action_id="demo.counter.set",
        inputs={"value": 100},
    )
    
    result = engine.execute_intent(project_id, intent, user_roles=["admin"])
    print(f"Execution Result: {result.status} - {result.message}")

    # 4. Verify that both snapshot and execution log exist
    latest_snapshot = repository.get_latest_snapshot(project_id)
    history = repository.get_execution_history(project_id)
    
    print(f"Snapshot saved: {latest_snapshot.snapshot_id if latest_snapshot else 'None'}")
    print(f"Audit log entry count: {len(history)}")
    
    if latest_snapshot and len(history) > 0:
        print("SUCCESS: Both state and audit log were persisted.")
        assert history[0].state_snapshot_id == latest_snapshot.snapshot_id
        print(f"Verified: Audit log refers to the correct snapshot ({history[0].state_snapshot_id})")
    else:
        print("FAILURE: Atomicity not verified.")

    print("\n--- Verifying Atomic Revert ---")
    
    # 5. Revert
    revert_res = engine.revert_to_snapshot(project_id, latest_snapshot.snapshot_id)
    print(f"Revert Result: {revert_res.status} - {revert_res.message}")
    
    history_after_revert = repository.get_execution_history(project_id)
    latest_snapshot_after_revert = repository.get_latest_snapshot(project_id)
    
    print(f"Total audit log entries: {len(history_after_revert)}")
    print(f"Latest Snapshot ID: {latest_snapshot_after_revert.snapshot_id}")
    
    if history_after_revert[0].action_id == "system.revert":
        assert history_after_revert[0].state_snapshot_id == latest_snapshot_after_revert.snapshot_id
        print("Verified: Revert action and resulting state were persisted atomically.")

if __name__ == "__main__":
    run_example()
