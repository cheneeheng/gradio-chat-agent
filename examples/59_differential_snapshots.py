"""Example of Differential Snapshots and State Reconstruction.

This example demonstrates how:
1. The system automatically creates differential snapshots instead of full-state checkpoints.
2. The state is reconstructed correctly by replaying deltas from the last checkpoint.
3. The database stores 'diffs' instead of full component blobs for non-checkpoints.
"""

from gradio_chat_agent.execution.engine import ExecutionEngine
from gradio_chat_agent.persistence.sql_repository import SQLStateRepository
from gradio_chat_agent.registry.in_memory import InMemoryRegistry
from gradio_chat_agent.registry.demo_actions import (
    counter_component,
    set_action,
    set_handler
)
from gradio_chat_agent.models.intent import ChatIntent
from gradio_chat_agent.models.enums import IntentType

def run_example():
    # Use SQL repository to inspect raw database content
    db_url = "sqlite:///:memory:"
    repository = SQLStateRepository(db_url)
    registry = InMemoryRegistry()
    engine = ExecutionEngine(registry, repository)
    project_id = "diff-snap-demo"

    registry.register_component(counter_component)
    registry.register_action(set_action, set_handler)

    print("--- Phase 1: Creating snapshots ---")
    
    # Heuristic: every 5th success is a checkpoint.
    # 1st success will be a checkpoint (success_count % 5 == 0 initially? 
    # wait, engine logic says: history = repo.get_execution_history(limit=10); success_count = sum(...)
    # If history is empty, success_count is 0. 0 % 5 == 0. So 1st is checkpoint.
    # 2nd success: history has 1 success. 1 % 5 == 1. Not a checkpoint.
    
    for i in range(1, 4):
        print(f"Executing step {i}: Set counter to {i*10}")
        intent = ChatIntent(
            type=IntentType.ACTION_CALL,
            request_id=f"req-{i}",
            action_id="demo.counter.set",
            inputs={"value": i*10}
        )
        engine.execute_intent(project_id, intent, user_roles=["admin"])

    # 2. Inspect Database
    print("\n--- Phase 2: Inspecting Database ---")
    from gradio_chat_agent.persistence.models import Snapshot
    with repository.SessionLocal() as session:
        from sqlalchemy import select
        snapshots = session.execute(select(Snapshot).order_by(Snapshot.timestamp)).scalars().all()
        
        for i, s in enumerate(snapshots):
            type_str = "CHECKPOINT" if s.is_checkpoint else "DELTA"
            parent = s.parent_id or "None"
            print(f"Snapshot {i}: ID={s.id[:8]}, Type={type_str}, Parent={parent[:8]}")
            if not s.is_checkpoint:
                print(f"  Content keys: {list(s.components.keys())} (should contain 'diffs')")
            else:
                print(f"  Content keys: {list(s.components.keys())} (should contain component IDs)")

    # 3. Verify State Reconstruction
    print("\n--- Phase 3: Verifying State Reconstruction ---")
    latest = repository.get_latest_snapshot(project_id)
    val = latest.components["demo.counter"]["value"]
    print(f"Latest Reconstructed Counter Value: {val} (Expected: 30)")
    assert val == 30

if __name__ == "__main__":
    run_example()
