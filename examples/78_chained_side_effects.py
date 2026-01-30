"""Example of Chained Side Effects using Hooks.

This example demonstrates how:
1. A post-execution hook can detect a specific action completion.
2. The hook then programmatically triggers a follow-up action.
3. This creates an automated "Cleanup" or "Sync" workflow.
"""

from gradio_chat_agent.execution.engine import ExecutionEngine
from gradio_chat_agent.persistence.in_memory import InMemoryStateRepository
from gradio_chat_agent.registry.in_memory import InMemoryRegistry
from gradio_chat_agent.registry.demo_actions import counter_component, set_action, set_handler, reset_action, reset_handler
from gradio_chat_agent.models.intent import ChatIntent
from gradio_chat_agent.models.enums import IntentType

def run_example():
    # 1. Setup system
    registry = InMemoryRegistry()
    repository = InMemoryStateRepository()
    engine = ExecutionEngine(registry, repository)
    project_id = "chain-demo"
    
    registry.register_component(counter_component)
    registry.register_action(set_action, set_handler)
    registry.register_action(reset_action, reset_handler)

    # 2. Define a Chained Hook
    def auto_reset_hook(pid: str, result):
        # Trigger reset automatically if value reaches 100
        if result.action_id == "demo.counter.set" and result.status == "success":
            val = result.state_diff[0].value if result.state_diff else 0
            if val >= 100:
                print(f"HOOK: Threshold reached ({val}). Triggering auto-reset...")
                reset_intent = ChatIntent(
                    type=IntentType.ACTION_CALL,
                    request_id=f"auto-reset-{result.request_id}",
                    action_id="demo.counter.reset",
                    inputs={},
                    confirmed=True
                )
                # Execute follow-up action (as system user)
                engine.execute_intent(pid, reset_intent, user_roles=["admin"], user_id="system_hooks")

    # 3. Register the hook
    engine.add_post_execution_hook(auto_reset_hook)

    # 4. Perform an action that triggers the chain
    print("--- Phase 1: Setting value to 50 (No chain) ---")
    engine.execute_intent(project_id, ChatIntent(type=IntentType.ACTION_CALL, request_id="r1", action_id="demo.counter.set", inputs={"value": 50}))
    
    # Check state
    snapshot = repository.get_latest_snapshot(project_id)
    print(f"Current Value: {snapshot.components['demo.counter']['value']}")

    print("\n--- Phase 2: Setting value to 150 (Triggers reset) ---")
    engine.execute_intent(project_id, ChatIntent(type=IntentType.ACTION_CALL, request_id="r2", action_id="demo.counter.set", inputs={"value": 150}))

    # 5. Verify final state
    final_snapshot = repository.get_latest_snapshot(project_id)
    final_val = final_snapshot.components['demo.counter']['value']
    print(f"Final Value after chain: {final_val} (Expected: 0)")
    assert final_val == 0

if __name__ == "__main__":
    run_example()
