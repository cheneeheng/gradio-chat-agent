"""Example of using the Standard Model/Inference Suite.

This example demonstrates how to:
1. Register standard model components and actions.
2. Select a model.
3. Load the model.
4. Run an inference.
"""

import uuid
from datetime import datetime

from gradio_chat_agent.execution.engine import ExecutionEngine
from gradio_chat_agent.models.enums import IntentType
from gradio_chat_agent.models.intent import ChatIntent
from gradio_chat_agent.models.state_snapshot import StateSnapshot
from gradio_chat_agent.persistence.in_memory import InMemoryStateRepository
from gradio_chat_agent.registry.in_memory import InMemoryRegistry
from gradio_chat_agent.registry.std_models import (
    model_selector_component,
    prompt_editor_component,
    output_panel_component,
    select_model_action,
    select_model_handler,
    load_model_action,
    load_model_handler,
    run_inference_action,
    run_inference_handler,
)


def run_example():
    # 1. Setup
    registry = InMemoryRegistry()
    repository = InMemoryStateRepository()
    engine = ExecutionEngine(registry, repository)
    project_id = "std-models-demo"

    # Register components
    registry.register_component(model_selector_component)
    registry.register_component(prompt_editor_component)
    registry.register_component(output_panel_component)

    # Register actions
    registry.register_action(select_model_action, select_model_handler)
    registry.register_action(load_model_action, load_model_handler)
    registry.register_action(run_inference_action, run_inference_handler)

    # Prepare initial state
    initial_snapshot = StateSnapshot(
        snapshot_id="init",
        components={
            "model.selector": {
                "selected_model": None,
                "loaded": False,
                "available_models": ["gpt-4o", "gpt-4o-mini"]
            },
            "prompt.editor": {"text": "What is the capital of France?"},
            "output.panel": {
                "latest_response": None,
                "streaming": False,
                "tokens_used": 0
            }
        },
    )
    repository.save_snapshot(project_id, initial_snapshot)

    print("--- Phase 1: Selecting a Model ---")
    intent_select = ChatIntent(
        type=IntentType.ACTION_CALL,
        request_id="req-1",
        action_id="model.select",
        inputs={"model_name": "gpt-4o"},
    )
    res1 = engine.execute_intent(project_id, intent_select, user_roles=["admin"])
    print(f"Result: {res1.status} - {res1.message}")

    print("\n--- Phase 2: Loading the Model ---")
    intent_load = ChatIntent(
        type=IntentType.ACTION_CALL,
        request_id="req-2",
        action_id="model.load",
        inputs={},
    )
    res2 = engine.execute_intent(project_id, intent_load, user_roles=["admin"])
    print(f"Result: {res2.status} - {res2.message}")

    print("\n--- Phase 3: Running Inference ---")
    intent_run = ChatIntent(
        type=IntentType.ACTION_CALL,
        request_id="req-3",
        action_id="inference.run",
        inputs={"prompt_override": "Explain quantum physics in one sentence."},
    )
    res3 = engine.execute_intent(project_id, intent_run, user_roles=["admin"])
    print(f"Result: {res3.status} - {res3.message}")

    # Final verification
    latest = repository.get_latest_snapshot(project_id)
    output = latest.components["output.panel"]
    print(f"\nFinal Inference Result: {output['latest_response']}")
    print(f"Tokens Used: {output['tokens_used']}")


if __name__ == "__main__":
    run_example()
