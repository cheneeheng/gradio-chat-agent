"""Example of using the Agent Layer and Session Memory.

This example demonstrates:
1. Setting up the OpenAIAgentAdapter.
2. Registering the system memory component and actions.
3. Using the agent to 'remember' a fact.
4. How the agent uses remembered context in subsequent turns.
"""

import os

from gradio_chat_agent.chat.openai_adapter import OpenAIAgentAdapter
from gradio_chat_agent.execution.engine import ExecutionEngine
from gradio_chat_agent.models.enums import ExecutionMode
from gradio_chat_agent.persistence.in_memory import InMemoryStateRepository
from gradio_chat_agent.registry.in_memory import InMemoryRegistry
from gradio_chat_agent.registry.system_actions import (
    memory_component,
    remember_action,
    remember_handler,
)


def run_example():
    # Ensure API Key is present for the adapter
    if not os.environ.get("OPENAI_API_KEY"):
        print("Error: OPENAI_API_KEY environment variable not set.")
        return

    # 1. Setup Infrastructure
    registry = InMemoryRegistry()
    repository = InMemoryStateRepository()
    engine = ExecutionEngine(registry, repository)
    adapter = OpenAIAgentAdapter()

    project_id = "memory-demo-project"

    # 2. Register System Memory
    registry.register_component(memory_component)
    registry.register_action(remember_action, remember_handler)

    print("--- Phase 1: Teaching the Agent a Fact ---")

    # User message that should trigger memory.remember
    user_msg = "Remember that my favorite color is teal."
    print(f"User: {user_msg}")

    # Fetch current state context for the agent
    snapshot = repository.get_latest_snapshot(project_id)
    state_dict = snapshot.components if snapshot else {}
    comp_reg = {
        c.component_id: c.model_dump() for c in registry.list_components()
    }
    act_reg = {a.action_id: a.model_dump() for a in registry.list_actions()}

    # Agent processes the message
    intent = adapter.message_to_intent_or_plan(
        message=user_msg,
        history=[],
        state_snapshot=state_dict,
        component_registry=comp_reg,
        action_registry=act_reg,
        execution_mode=ExecutionMode.ASSISTED,
        facts={},
    )

    if intent.type == "action_call" and intent.action_id == "memory.remember":
        print(
            f"Agent proposes: {intent.action_id}(key='{intent.inputs['key']}', value='{intent.inputs['value']}')"
        )

        # Execute the memory action (user_id is required for memory actions)
        result = engine.execute_intent(
            project_id, intent, user_roles=["admin"], user_id="admin"
        )
        print(f"Engine: {result.message}")
    else:
        print(f"Agent did not propose expected action. Got: {intent.type}")
        return

    print("\n--- Phase 2: Verifying Context Recall ---")

    # Now ask the agent a question based on that memory
    user_msg_2 = "What is my favorite color?"
    print(f"User: {user_msg_2}")

    # Fetch updated facts from repository
    facts = repository.get_session_facts(project_id, "admin")

    # Update history for context
    history = [
        {"role": "user", "content": user_msg},
        {
            "role": "assistant",
            "content": "I've remembered that your favorite color is teal.",
        },
    ]

    intent_2 = adapter.message_to_intent_or_plan(
        message=user_msg_2,
        history=history,
        state_snapshot={},
        component_registry=comp_reg,
        action_registry=act_reg,
        execution_mode=ExecutionMode.ASSISTED,
        facts=facts,
    )

    # In this case, the agent should ideally respond with a clarification/answer
    # since it sees the fact in the 'sys.memory' component state.
    if intent_2.type == "clarification_request":
        print(f"Agent: {intent_2.question}")
    else:
        print(f"Agent proposed an action: {intent_2.action_id}")


if __name__ == "__main__":
    run_example()
