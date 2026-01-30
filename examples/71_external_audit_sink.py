"""Example of an External Audit Sink using Post-Execution Hooks.

This example demonstrates how to:
1. Register a post-execution hook in the engine.
2. Stream successful execution results to an external file (audit.jsonl).
3. Filter which data is exported to the sink.
"""

import json
import os
from gradio_chat_agent.execution.engine import ExecutionEngine
from gradio_chat_agent.persistence.in_memory import InMemoryStateRepository
from gradio_chat_agent.registry.in_memory import InMemoryRegistry
from gradio_chat_agent.registry.demo_actions import counter_component, set_action, set_handler
from gradio_chat_agent.models.intent import ChatIntent
from gradio_chat_agent.models.enums import IntentType

def run_example():
    # 1. Setup system
    registry = InMemoryRegistry()
    repository = InMemoryStateRepository()
    engine = ExecutionEngine(registry, repository)
    project_id = "audit-sink-demo"
    
    registry.register_component(counter_component)
    registry.register_action(set_action, set_handler)

    # 2. Define the Audit Sink Hook
    AUDIT_FILE = "external_audit.jsonl"
    if os.path.exists(AUDIT_FILE):
        os.remove(AUDIT_FILE)

    def audit_sink_hook(pid: str, result):
        """Side effect: write success log to a separate file."""
        log_entry = {
            "project_id": pid,
            "request_id": result.request_id,
            "action": result.action_id,
            "user": result.user_id,
            "timestamp": result.timestamp.isoformat(),
            "cost": result.cost,
            "diff_summary": [d.path for d in result.state_diff]
        }
        
        with open(AUDIT_FILE, "a") as f:
            f.write(json.dumps(log_entry) + "\n")
        
        print(f"SINK: Appended audit log for {result.request_id} to {AUDIT_FILE}")

    # 3. Register the hook
    engine.add_post_execution_hook(audit_sink_hook)

    # 4. Perform some actions
    print("--- Executing Actions ---")
    for i in range(3):
        intent = ChatIntent(
            type=IntentType.ACTION_CALL,
            request_id=f"req-{i}",
            action_id="demo.counter.set",
            inputs={"value": i * 100}
        )
        engine.execute_intent(project_id, intent, user_id="alice_dev", user_roles=["admin"])

    # 5. Verify the external file
    print("\n--- Verifying External Audit Sink ---")
    if os.path.exists(AUDIT_FILE):
        with open(AUDIT_FILE, "r") as f:
            lines = f.readlines()
            print(f"Total entries in {AUDIT_FILE}: {len(lines)}")
            for line in lines:
                data = json.loads(line)
                print(f"  - [{data['timestamp']}] {data['action']} (Cost: {data['cost']})")
    
    # Cleanup
    if os.path.exists(AUDIT_FILE):
        os.remove(AUDIT_FILE)

if __name__ == "__main__":
    run_example()
