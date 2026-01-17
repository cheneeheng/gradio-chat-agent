"""Example of Project Lifecycle Enforcement (Archiving).

This example demonstrates how to:
1. Archive a project to prevent further executions.
2. Observe the engine rejecting intents for archived projects.
3. Verify that the project remains in the system but is effectively 'Read-Only'.
"""

import uuid

from gradio_chat_agent.execution.engine import ExecutionEngine
from gradio_chat_agent.models.action import (
    ActionDeclaration,
    ActionPermission,
)
from gradio_chat_agent.models.enums import (
    ActionRisk,
    ActionVisibility,
    IntentType,
)
from gradio_chat_agent.models.intent import ChatIntent
from gradio_chat_agent.persistence.in_memory import InMemoryStateRepository
from gradio_chat_agent.registry.in_memory import InMemoryRegistry


def run_example():
    registry = InMemoryRegistry()
    repository = InMemoryStateRepository()
    engine = ExecutionEngine(registry, repository)
    project_id = "lifecycle-demo"
    repository.create_project(project_id, "Lifecycle Demo")

    # Register a simple action
    action = ActionDeclaration(
        action_id="demo.action",
        title="Test Action",
        description="A simple action.",
        targets=["demo"],
        input_schema={},
        permission=ActionPermission(
            confirmation_required=False,
            risk=ActionRisk.LOW,
            visibility=ActionVisibility.USER,
        ),
    )
    registry.register_action(action, lambda i, s: ({}, [], "Done"))

    # 1. Active State
    print("--- Phase 1: Project Active ---")
    intent = ChatIntent(
        type=IntentType.ACTION_CALL,
        request_id=str(uuid.uuid4()),
        action_id="demo.action",
        inputs={},
    )
    res1 = engine.execute_intent(project_id, intent)
    print(f"Execution on active project: {res1.status}")

    # 2. Archive Project
    print("\n--- Phase 2: Archiving Project ---")
    repository.archive_project(project_id)
    print(f"Project '{project_id}' has been archived.")

    # 3. Attempt Execution on Archived Project
    intent2 = ChatIntent(
        type=IntentType.ACTION_CALL,
        request_id=str(uuid.uuid4()),
        action_id="demo.action",
        inputs={},
    )
    res2 = engine.execute_intent(project_id, intent2)
    print(f"Execution on archived project: {res2.status}")
    if res2.error:
        print(f"Error Code: {res2.error.code}")
        print(f"Error Detail: {res2.error.detail}")

    # 4. Verification
    is_archived = repository.is_project_archived(project_id)
    print(f"\nFinal status check: Archived? {is_archived}")


if __name__ == "__main__":
    run_example()
