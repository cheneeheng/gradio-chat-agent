"Example of using the Standard Library Components and Actions.

This example demonstrates how to:
1. Register standard library components (text.input, slider, status.indicator).
2. Execute actions to update these components.
3. Observe state changes.
"

import uuid
from datetime import datetime

from gradio_chat_agent.execution.engine import ExecutionEngine
from gradio_chat_agent.models.enums import IntentType
from gradio_chat_agent.models.intent import ChatIntent
from gradio_chat_agent.models.state_snapshot import StateSnapshot
from gradio_chat_agent.persistence.in_memory import InMemoryStateRepository
from gradio_chat_agent.registry.in_memory import InMemoryRegistry
from gradio_chat_agent.registry.std_lib import (
    text_input_component,
    text_input_set_action,
    text_input_set_handler,
    slider_component,
    slider_set_action,
    slider_set_handler,
    status_indicator_component,
    status_indicator_update_action,
    status_indicator_update_handler,
    TEXT_INPUT_ID,
    SLIDER_ID,
    STATUS_INDICATOR_ID,
)


def run_example():
    # 1. Setup
    registry = InMemoryRegistry()
    repository = InMemoryStateRepository()
    engine = ExecutionEngine(registry, repository)
    project_id = "std-lib-demo"

    # Register components
    registry.register_component(text_input_component)
    registry.register_component(slider_component)
    registry.register_component(status_indicator_component)

    # Register actions
    registry.register_action(text_input_set_action, text_input_set_handler)
    registry.register_action(slider_set_action, slider_set_handler)
    registry.register_action(status_indicator_update_action, status_indicator_update_handler)

    # Prepare initial state
    initial_snapshot = StateSnapshot(
        snapshot_id="init",
        components={
            TEXT_INPUT_ID: {"value": "", "label": "Search"},
            SLIDER_ID: {"value": 50, "min": 0, "max": 100},
            STATUS_INDICATOR_ID: {
                "status": "online",
                "message": "System ready."
            }
        },
    )
    repository.save_snapshot(project_id, initial_snapshot)

    print("--- Initial State ---")
    for cid, state in initial_snapshot.components.items():
        print(f"{cid}: {state}")

    # 2. Update Text Input
    print("\n--- Phase 1: Updating Text Input ---")
    intent_text = ChatIntent(
        type=IntentType.ACTION_CALL,
        request_id="req-1",
        action_id="std.text.input.set",
        inputs={"value": "Hello World"},
    )
    res1 = engine.execute_intent(project_id, intent_text, user_roles=["admin"])
    print(f"Result: {res1.status} - {res1.message}")

    # 3. Update Slider
    print("\n--- Phase 2: Updating Slider ---")
    intent_slider = ChatIntent(
        type=IntentType.ACTION_CALL,
        request_id="req-2",
        action_id="std.slider.set",
        inputs={"value": 75.5},
    )
    res2 = engine.execute_intent(project_id, intent_slider, user_roles=["admin"])
    print(f"Result: {res2.status} - {res2.message}")

    # 4. Update Status Indicator
    print("\n--- Phase 3: Updating Status Indicator ---")
    intent_status = ChatIntent(
        type=IntentType.ACTION_CALL,
        request_id="req-3",
        action_id="std.status.indicator.update",
        inputs={"status": "busy", "message": "Processing request..."},
    )
    res3 = engine.execute_intent(project_id, intent_status, user_roles=["admin"])
    print(f"Result: {res3.status} - {res3.message}")

    # Final verification
    latest = repository.get_latest_snapshot(project_id)
    print("\n--- Final State ---")
    for cid, state in latest.components.items():
        print(f"{cid}: {state}")


if __name__ == "__main__":
    run_example()