"""Example of State Integrity Verification.

This example demonstrates how the system detects unauthorized modifications
to the state by verifying the SHA-256 checksum of the latest snapshot.
"""

import uuid
from datetime import datetime

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
from gradio_chat_agent.utils import compute_checksum


def run_example():
    # 1. Setup
    registry = InMemoryRegistry()
    repository = InMemoryStateRepository()
    engine = ExecutionEngine(registry, repository)
    project_id = "integrity-demo"

    registry.register_component(counter_component)
    registry.register_action(set_action, set_handler)

    # 2. Perform a legitimate action
    print("--- Phase 1: Legitimate Execution ---")
    intent1 = ChatIntent(
        type=IntentType.ACTION_CALL,
        request_id="req-1",
        action_id="demo.counter.set",
        inputs={"value": 10},
    )
    res1 = engine.execute_intent(project_id, intent1, user_roles=["admin"])
    print(f"Result: {res1.status} - {res1.message}")

    latest = repository.get_latest_snapshot(project_id)
    print(f"Current Value: {latest.components['demo.counter']['value']}")
    print(f"Stored Checksum: {latest.checksum[:16]}...")

    # 3. Simulate unauthorized modification (Tampering)
    print("\n--- Phase 2: Unauthorized Tampering ---")
    
    # We manually modify the components in the "database" WITHOUT updating the checksum
    latest.components["demo.counter"]["value"] = 999 
    repository.save_snapshot(project_id, latest)
    
    print("State tampered! Value set to 999 but checksum is for value 10.")

    # 4. Attempt another action
    print("\n--- Phase 3: Detection ---")
    intent2 = ChatIntent(
        type=IntentType.ACTION_CALL,
        request_id="req-2",
        action_id="demo.counter.set",
        inputs={"value": 20},
    )
    
    res2 = engine.execute_intent(project_id, intent2, user_roles=["admin"])
    
    if res2.status == "failed" and res2.error.code == "integrity_violation":
        print(f"ALERT: {res2.message}")
        print("System successfully blocked execution due to integrity violation.")
    else:
        print(f"Warning: Integrity violation NOT detected. Status: {res2.status}")


if __name__ == "__main__":
    run_example()
