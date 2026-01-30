""
Example 81: Gemini Adapter Demo

This example demonstrates how to programmatically use the GeminiAgentAdapter
to interact with the Gemini API.

Prerequisites:
    - Set GOOGLE_API_KEY environment variable.
    - Set LLM_PROVIDER=gemini (optional for this script since we instantiate directly,
      but good practice).
""

import os
import sys
from typing import Any

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "src"))

from gradio_chat_agent.chat.gemini_adapter import GeminiAgentAdapter
from gradio_chat_agent.models.intent import ChatIntent


def main():
    if not os.environ.get("GOOGLE_API_KEY"):
        print("Error: GOOGLE_API_KEY not set.")
        return

    print("Initializing GeminiAgentAdapter...")
    # You can specify a model, e.g., "gemini-1.5-pro"
    adapter = GeminiAgentAdapter(model_name="gemini-2.0-flash")

    # Define a simple registry (mocking what the engine does)
    action_registry = {
        "hello_world": {
            "description": "Prints hello world.",
            "input_schema": {"type": "object", "properties": {}},
        },
        "calculate_sum": {
            "description": "Calculates the sum of two numbers.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "a": {"type": "number"},
                    "b": {"type": "number"}
                },
                "required": ["a", "b"]
            }
        }
    }

    component_registry = {
        "console": {
            "description": "The system console.",
            "permissions": {},
            "invariants": []
        }
    }

    # Simulate a conversation history
    history = []
    
    # 1. Simple greeting (likely no action)
    print("\n--- Turn 1: User says 'Hi' ---")
    intent = adapter.message_to_intent_or_plan(
        message="Hi there!",
        history=history,
        state_snapshot={},
        component_registry=component_registry,
        action_registry=action_registry
    )
    print(f"Result: {intent}")
    
    # Update history
    history.append({"role": "user", "content": "Hi there!"})
    if isinstance(intent, ChatIntent):
        history.append({"role": "assistant", "content": intent.question or "Hello!"})

    # 2. Requesting an action
    print("\n--- Turn 2: User says 'Calculate 5 + 3' ---")
    intent = adapter.message_to_intent_or_plan(
        message="Please calculate the sum of 5 and 3.",
        history=history,
        state_snapshot={},
        component_registry=component_registry,
        action_registry=action_registry
    )
    
    print(f"Result Type: {type(intent)}")
    if isinstance(intent, ChatIntent):
        print(f"Action ID: {intent.action_id}")
        print(f"Inputs: {intent.inputs}")
    else:
        # ExecutionPlan
        print(f"Plan Steps: {len(intent.steps)}")
        for step in intent.steps:
            print(f"  - Action: {step.action_id}, Inputs: {step.inputs}")

if __name__ == "__main__":
    main()
