"""Example of using SQL Persistence and Rate Limiting.

This example demonstrates:
1. Using the SQLStateRepository (SQLite).
2. Setting project-level governance limits (Rate Limiting).
3. Triggering a rate limit violation.
4. Inspecting the persistent audit log.
"""

import uuid

from gradio_chat_agent.execution.engine import ExecutionEngine
from gradio_chat_agent.models.enums import ExecutionStatus, IntentType
from gradio_chat_agent.models.intent import ChatIntent
from gradio_chat_agent.persistence.sql_repository import SQLStateRepository
from gradio_chat_agent.registry.demo_actions import (
    counter_component,
    set_action,
    set_handler,
)
from gradio_chat_agent.registry.in_memory import InMemoryRegistry


def run_example():
    # 1. Setup SQL Persistence (using in-memory SQLite for this demo)
    # In production, use "postgresql://user:pass@localhost/dbname"
    db_url = "sqlite:///:memory:"
    print(f"Initializing SQL Repository with {db_url}...")
    repository = SQLStateRepository(db_url)

    registry = InMemoryRegistry()
    engine = ExecutionEngine(registry, repository)
    project_id = "limit-demo-project"

    # 2. Register Actions
    registry.register_component(counter_component)
    registry.register_action(set_action, set_handler)

    # 3. Define and Apply Policy
    # Limit: 2 actions per minute
    print(
        f"Setting rate limit for project '{project_id}' to 2 actions/minute."
    )
    policy = {"limits": {"rate": {"per_minute": 2}}}
    repository.set_project_limits(project_id, policy)

    # 4. Attempt Executions
    print("\n--- Starting Execution Loop ---")

    for i in range(1, 5):
        print(f"Attempt {i}: Setting counter to {i}")

        intent = ChatIntent(
            type=IntentType.ACTION_CALL,
            request_id=str(uuid.uuid4()),
            action_id="demo.counter.set",
            inputs={"value": i},
        )

        result = engine.execute_intent(
            project_id, intent, user_roles=["admin"]
        )

        if result.status == ExecutionStatus.SUCCESS:
            print(f"Result: SUCCESS (Msg: {result.message})")
        else:
            print(f"Result: {result.status} (Error: {result.message})")

    # 5. Inspect Audit Log
    print("\n--- Audit Log Inspection (Last 5) ---")
    history = repository.get_execution_history(project_id, limit=5)
    for entry in history:
        print(f"[{entry.timestamp}] {entry.action_id} -> {entry.status}")


if __name__ == "__main__":
    run_example()
