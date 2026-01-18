"""Example of using Async Observers for background tasks.

This example demonstrates how to:
1. Initialize the AuditLogObserver.
2. Register a callback that reacts to state changes.
3. Observe the callback being triggered asynchronously after an execution.
"""

import time
from gradio_chat_agent.execution.engine import ExecutionEngine
from gradio_chat_agent.execution.observer import AuditLogObserver
from gradio_chat_agent.models.enums import IntentType
from gradio_chat_agent.models.intent import ChatIntent
from gradio_chat_agent.persistence.in_memory import InMemoryStateRepository
from gradio_chat_agent.registry.demo_actions import counter_component, set_action, set_handler
from gradio_chat_agent.registry.in_memory import InMemoryRegistry

def run_example():
    # 1. Setup system
    registry = InMemoryRegistry()
    repository = InMemoryStateRepository()
    engine = ExecutionEngine(registry, repository)
    project_id = "async-obs-demo"
    repository.create_project(project_id, "Async Observer Demo")

    registry.register_component(counter_component)
    registry.register_action(set_action, set_handler)

    # 2. Setup Observer (fast polling for demo)
    observer = AuditLogObserver(engine, poll_interval=1.0)
    
    observed_actions = []
    def my_async_task(pid, result):
        print(f"ASYNC: Processing successful action {result.action_id} for project {pid}")
        observed_actions.append(result.action_id)

    observer.add_callback(my_async_task)
    observer.start()

    try:
        print("--- Step 1: Performing an action ---")
        intent = ChatIntent(
            type=IntentType.ACTION_CALL,
            request_id="req-1",
            action_id="demo.counter.set",
            inputs={"value": 42}
        )
        engine.execute_intent(project_id, intent, user_roles=["admin"])
        print("Action executed by engine.")

        print("\nWaiting for async observer to detect change...")
        # Give it a few seconds to poll
        for _ in range(5):
            if observed_actions:
                break
            time.sleep(1)

        print(f"\nActions observed asynchronously: {observed_actions}")
        assert "demo.counter.set" in observed_actions

    finally:
        observer.stop()

if __name__ == "__main__":
    run_example()
