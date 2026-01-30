"""Example of Governed Session Memory Interception.

This example demonstrates how:
1. Memory actions (remember/forget) are intercepted by the ExecutionEngine.
2. Facts are stored in the authoritative repository table, NOT the component state.
3. User-scoping is enforced for these facts.
"""

from gradio_chat_agent.execution.engine import ExecutionEngine
from gradio_chat_agent.models.enums import IntentType
from gradio_chat_agent.models.intent import ChatIntent
from gradio_chat_agent.persistence.in_memory import InMemoryStateRepository
from gradio_chat_agent.registry.in_memory import InMemoryRegistry
from gradio_chat_agent.registry.system_actions import (
    forget_action,
    forget_handler,
    remember_action,
    remember_handler,
)


def run_example():
    # 1. Setup
    registry = InMemoryRegistry()
    repository = InMemoryStateRepository()
    engine = ExecutionEngine(registry, repository)

    project_id = "memory-governance-demo"
    user_id = "alice-123"

    # Register handlers (though engine intercepts them, they must still exist in registry)
    registry.register_action(remember_action, remember_handler)
    registry.register_action(forget_action, forget_handler)

    # 2. Execute 'memory.remember'
    print("--- Phase 1: Storing a Fact ---")
    intent = ChatIntent(
        type=IntentType.ACTION_CALL,
        request_id="mem-1",
        action_id="memory.remember",
        inputs={"key": "experience_level", "value": "expert"},
    )

    # Note: user_id is now required for memory actions
    res = engine.execute_intent(project_id, intent, user_id=user_id)
    print(f"Engine: {res.message}")

    # 3. Verify Storage Location
    print("\n--- Phase 2: Verifying Integrity ---")

    # Check Component State (Should be EMPTY)
    snapshot = repository.get_latest_snapshot(project_id)
    # The result.state_snapshot_id was "no_snapshot"
    print(f"Snapshot ID recorded: {res.state_snapshot_id}")
    if snapshot is None:
        print("Confirmed: Component state was NOT mutated.")

    # Check Fact Table (Should contain the value)
    facts = repository.get_session_facts(project_id, user_id)
    print(f"Facts in Repository for {user_id}: {facts}")

    # 4. Verify User Isolation
    print("\n--- Phase 3: Verifying Isolation ---")
    bob_facts = repository.get_session_facts(project_id, "bob-456")
    print(f"Facts for bob-456: {bob_facts} (Expected: empty)")

    # 5. Forget
    print("\n--- Phase 4: Forgetting ---")
    forget_intent = ChatIntent(
        type=IntentType.ACTION_CALL,
        request_id="mem-2",
        action_id="memory.forget",
        inputs={"key": "experience_level"},
    )
    engine.execute_intent(project_id, forget_intent, user_id=user_id)

    final_facts = repository.get_session_facts(project_id, user_id)
    print(f"Final Facts for {user_id}: {final_facts}")


if __name__ == "__main__":
    run_example()
