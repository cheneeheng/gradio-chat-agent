"""Example of the Agent controlling a Demo Counter.

This example shows the end-to-end flow of:
1. User asking to change a UI component (Counter).
2. Agent selecting the correct action (demo.counter.set).
3. Engine executing the action and updating the state.
"""

import os

from gradio_chat_agent.chat.openai_adapter import OpenAIAgentAdapter
from gradio_chat_agent.execution.engine import ExecutionEngine
from gradio_chat_agent.persistence.in_memory import InMemoryStateRepository
from gradio_chat_agent.registry.demo_actions import (
    counter_component,
    increment_action,
    increment_handler,
    set_action,
    set_handler,
)
from gradio_chat_agent.registry.in_memory import InMemoryRegistry


def run_example():
    if not os.environ.get("OPENAI_API_KEY"):
        print("Error: OPENAI_API_KEY not set.")
        return

    # 1. Setup
    registry = InMemoryRegistry()
    repository = InMemoryStateRepository()
    engine = ExecutionEngine(registry, repository)
    adapter = OpenAIAgentAdapter()
    project_id = "counter-demo"

    # 2. Register Counter
    registry.register_component(counter_component)
    registry.register_action(set_action, set_handler)
    registry.register_action(increment_action, increment_handler)

    print("--- Initial State ---")
    # State is empty initially, engine will initialize it on first execute or we can save a snapshot
    print("Counter state: Not initialized")

    # 3. User request: "Set counter to 10"
    user_msg = "Please set the counter to 10."
    print(f"\nUser: {user_msg}")

    comp_reg = {
        c.component_id: c.model_dump() for c in registry.list_components()
    }
    act_reg = {a.action_id: a.model_dump() for a in registry.list_actions()}

    intent = adapter.message_to_intent_or_plan(
        message=user_msg,
        history=[],
        state_snapshot={},
        component_registry=comp_reg,
        action_registry=act_reg,
    )

    if intent.type == "action_call":
        print(f"Agent proposes: {intent.action_id}({intent.inputs})")
        res = engine.execute_intent(project_id, intent, user_roles=["admin"])
        print(f"Engine: {res.message}")

    # 4. User request: "Add 5 more"
    user_msg_2 = "Add 5 more to the counter."
    print(f"\nUser: {user_msg_2}")

    # Fetch updated state
    snapshot = repository.get_latest_snapshot(project_id)
    current_state = snapshot.components if snapshot else {}

    intent_2 = adapter.message_to_intent_or_plan(
        message=user_msg_2,
        history=[
            {"role": "user", "content": user_msg},
            {"role": "assistant", "content": "Counter set to 10."},
        ],
        state_snapshot=current_state,
        component_registry=comp_reg,
        action_registry=act_reg,
    )

    if intent_2.type == "action_call":
        print(f"Agent proposes: {intent_2.action_id}({intent_2.inputs})")
        res = engine.execute_intent(project_id, intent_2, user_roles=["admin"])
        print(f"Engine: {res.message}")

    # Final verification
    final_snapshot = repository.get_latest_snapshot(project_id)
    print(f"\nFinal State: {final_snapshot.components['demo.counter']}")


if __name__ == "__main__":
    run_example()
