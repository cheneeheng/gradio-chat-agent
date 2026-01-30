"""Example of State Reconstruction (Time Travel).

This example demonstrates how to:
1. Perform a series of actions.
2. Use reconstruct_state to see what the state was at a specific point in time.
3. Verify that the reconstruction matches the historical state.
"""

import time
from gradio_chat_agent.execution.engine import ExecutionEngine
from gradio_chat_agent.models.enums import IntentType
from gradio_chat_agent.models.intent import ChatIntent
from gradio_chat_agent.persistence.in_memory import InMemoryStateRepository
from gradio_chat_agent.registry.demo_actions import counter_component, set_action, set_handler
from gradio_chat_agent.registry.in_memory import InMemoryRegistry

def run_example():
    # 1. Setup
    registry = InMemoryRegistry()
    repository = InMemoryStateRepository()
    engine = ExecutionEngine(registry, repository)
    project_id = "reconstruction-demo"

    registry.register_component(counter_component)
    registry.register_action(set_action, set_handler)

    # 2. Perform actions
    print("Performing Step 1: Set counter to 10")
    req1 = "req-1"
    engine.execute_intent(project_id, ChatIntent(type=IntentType.ACTION_CALL, request_id=req1, action_id="demo.counter.set", inputs={"value": 10}))
    
    print("Performing Step 2: Set counter to 20")
    req2 = "req-2"
    engine.execute_intent(project_id, ChatIntent(type=IntentType.ACTION_CALL, request_id=req2, action_id="demo.counter.set", inputs={"value": 20}))
    
    print("Performing Step 3: Set counter to 30")
    req3 = "req-3"
    engine.execute_intent(project_id, ChatIntent(type=IntentType.ACTION_CALL, request_id=req3, action_id="demo.counter.set", inputs={"value": 30}))

    # 3. Reconstruct
    print("\n--- Reconstructing state at Step 2 ---")
    reconstructed = engine.reconstruct_state(project_id, target_request_id=req2)
    
    val = reconstructed.get("demo.counter", {}).get("value")
    print(f"Reconstructed Counter Value: {val} (Expected: 20)")
    assert val == 20

    print("\n--- Reconstructing state at Step 1 ---")
    reconstructed_1 = engine.reconstruct_state(project_id, target_request_id=req1)
    val_1 = reconstructed_1.get("demo.counter", {}).get("value")
    print(f"Reconstructed Counter Value: {val_1} (Expected: 10)")
    assert val_1 == 10

    print("\n--- Reconstructing full state (Step 3) ---")
    reconstructed_full = engine.reconstruct_state(project_id)
    val_full = reconstructed_full.get("demo.counter", {}).get("value")
    print(f"Reconstructed Counter Value: {val_full} (Expected: 30)")
    assert val_full == 30

if __name__ == "__main__":
    run_example()
