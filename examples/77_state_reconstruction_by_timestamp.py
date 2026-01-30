"""Example of State Reconstruction by Timestamp.

This example demonstrates how to:
1. Perform actions over a period of time.
2. Use reconstruct_state with a target_timestamp to see the state at that moment.
3. Verify the state matches what was expected at that specific time.
"""

import time
from datetime import datetime, timezone, timedelta
from gradio_chat_agent.execution.engine import ExecutionEngine
from gradio_chat_agent.persistence.in_memory import InMemoryStateRepository
from gradio_chat_agent.registry.in_memory import InMemoryRegistry
from gradio_chat_agent.registry.demo_actions import counter_component, set_action, set_handler
from gradio_chat_agent.models.intent import ChatIntent
from gradio_chat_agent.models.enums import IntentType

def run_example():
    # 1. Setup
    registry = InMemoryRegistry()
    repository = InMemoryStateRepository()
    engine = ExecutionEngine(registry, repository)
    project_id = "timestamp-demo"

    registry.register_component(counter_component)
    registry.register_action(set_action, set_handler)

    # 2. Perform actions with artificial delays
    print("Step 1: Set counter to 10")
    engine.execute_intent(project_id, ChatIntent(type=IntentType.ACTION_CALL, request_id="r1", action_id="demo.counter.set", inputs={"value": 10}))
    
    # Capture timestamp after first action
    checkpoint_time = datetime.now(timezone.utc) + timedelta(milliseconds=500)
    print(f"Checkpoint T1 recorded: {checkpoint_time}")
    
    time.sleep(1) # Ensure clear separation
    
    print("Step 2: Set counter to 20")
    engine.execute_intent(project_id, ChatIntent(type=IntentType.ACTION_CALL, request_id="r2", action_id="demo.counter.set", inputs={"value": 20}))

    # 3. Reconstruct at Checkpoint Time
    print(f"\n--- Reconstructing state at T1 ---")
    reconstructed = engine.reconstruct_state(project_id, target_timestamp=checkpoint_time)
    
    val = reconstructed.get("demo.counter", {}).get("value")
    print(f"Reconstructed Value: {val} (Expected: 10)")
    assert val == 10

    # 4. Reconstruct at Current Time
    print("\n--- Reconstructing state at current time ---")
    reconstructed_now = engine.reconstruct_state(project_id)
    val_now = reconstructed_now.get("demo.counter", {}).get("value")
    print(f"Reconstructed Value: {val_now} (Expected: 20)")
    assert val_now == 20
    
    print("\nSUCCESS: State correctly reconstructed by timestamp.")

if __name__ == "__main__":
    run_example()
