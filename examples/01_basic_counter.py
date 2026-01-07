"""Basic example of the Gradio Chat Agent execution engine.

This example demonstrates how to:
1. Register a component and an action.
2. Initialize the execution engine.
3. Execute a 'set' action via a structured intent.
4. Inspect the resulting state and audit log.
"""

import uuid
from datetime import datetime
from typing import Any

from gradio_chat_agent.execution.engine import ExecutionEngine
from gradio_chat_agent.models.action import (
    ActionDeclaration,
    ActionPermission,
)
from gradio_chat_agent.models.component import (
    ComponentDeclaration,
    ComponentPermissions,
)
from gradio_chat_agent.models.enums import (
    ActionRisk,
    ActionVisibility,
    IntentType,
)
from gradio_chat_agent.models.intent import ChatIntent
from gradio_chat_agent.models.state_snapshot import StateSnapshot
from gradio_chat_agent.persistence.repository import InMemoryStateRepository
from gradio_chat_agent.registry.in_memory import InMemoryRegistry


def run_example():
    # 1. Initialize the components of the system
    registry = InMemoryRegistry()
    repository = InMemoryStateRepository()
    engine = ExecutionEngine(registry, repository)
    project_id = "example-project"

    # 2. Register a 'Counter' component
    counter_comp = ComponentDeclaration(
        component_id="demo.counter",
        title="Counter",
        description="A simple numerical counter.",
        state_schema={
            "type": "object",
            "properties": {"value": {"type": "integer"}},
            "required": ["value"],
        },
        permissions=ComponentPermissions(readable=True),
    )
    registry.register_component(counter_comp)

    # 3. Register a 'Set' action for the counter
    set_action = ActionDeclaration(
        action_id="demo.counter.set",
        title="Set Value",
        description="Sets the counter to a specific integer value.",
        targets=["demo.counter"],
        input_schema={
            "type": "object",
            "properties": {"value": {"type": "integer"}},
            "required": ["value"],
        },
        permission=ActionPermission(
            confirmation_required=False,
            risk=ActionRisk.LOW,
            visibility=ActionVisibility.USER,
        ),
    )

    def set_handler(inputs: dict[str, Any], snapshot: StateSnapshot):
        """Pure handler that returns the new state."""
        new_value = inputs["value"]
        new_components = snapshot.components.copy()
        new_components["demo.counter"] = {"value": new_value}
        return new_components, [], f"Counter set to {new_value}"

    registry.register_action(set_action, set_handler)

    # 4. Prepare an initial state
    initial_snapshot = StateSnapshot(
        snapshot_id=str(uuid.uuid4()),
        timestamp=datetime.now(),
        components={"demo.counter": {"value": 0}},
    )
    repository.save_snapshot(project_id, initial_snapshot)

    print(f"Initial State: {initial_snapshot.components['demo.counter']}")

    # 5. Create and execute an intent (The Agent Layer would do this)
    intent = ChatIntent(
        type=IntentType.ACTION_CALL,
        request_id=f"req-{uuid.uuid4().hex[:8]}",
        action_id="demo.counter.set",
        inputs={"value": 42},
    )

    print(f"\nExecuting Action: {intent.action_id} with value 42...")
    result = engine.execute_intent(project_id, intent, user_roles=["operator"])

    # 6. Inspect the result
    if result.status == "success":
        print(f"Success! Message: {result.message}")
        print(f"Diff applied: {result.state_diff}")

        # Fetch the new state from the repository
        latest = repository.get_latest_snapshot(project_id)
        state = (latest.components if latest else {}).get("demo.counter")
        print(f"New State: {state}")
    else:
        detail = getattr(result.error, "detail", None)
        print(f"Execution Failed: {detail}")


if __name__ == "__main__":
    run_example()
