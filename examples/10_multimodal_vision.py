"""Example of Multimodal Vision Support and Media Hashing.

This example demonstrates how to:
1. Pass media (images) to the OpenAIAgentAdapter.
2. How the adapter constructs vision-capable message parts.
3. How the execution engine computes and stores media hashes in metadata.
"""

import os

from gradio_chat_agent.chat.openai_adapter import OpenAIAgentAdapter
from gradio_chat_agent.execution.engine import ExecutionEngine
from gradio_chat_agent.models.enums import IntentType, MediaType
from gradio_chat_agent.models.intent import ChatIntent, IntentMedia
from gradio_chat_agent.persistence.in_memory import InMemoryStateRepository
from gradio_chat_agent.registry.demo_actions import (
    counter_component,
    set_action,
    set_handler,
)
from gradio_chat_agent.registry.in_memory import InMemoryRegistry


def run_example():
    # 1. Setup
    registry = InMemoryRegistry()
    repository = InMemoryStateRepository()
    engine = ExecutionEngine(registry, repository)

    # Placeholder for OpenAI (requires vision-capable model like gpt-4o)
    adapter = OpenAIAgentAdapter(model_name="gpt-4o")
    project_id = "vision-demo"

    registry.register_component(counter_component)
    registry.register_action(set_action, set_handler)

    # 2. Simulate a base64 encoded image (tiny transparent pixel)
    image_data = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8/5+hHgAHggJ/PchI7wAAAABJRU5ErkJggg=="
    media = IntentMedia(
        type=MediaType.IMAGE, data=image_data, mime_type="image/png"
    )

    print("--- Phase 1: Agent Vision Interpretation ---")
    if not os.environ.get("OPENAI_API_KEY"):
        print("Skipping LLM call: OPENAI_API_KEY not set.")
        # Construct a manual intent for demonstration of the engine part
        intent = ChatIntent(
            type=IntentType.ACTION_CALL,
            request_id="vision-req-1",
            action_id="demo.counter.set",
            inputs={"value": 5},
            media=media,
        )
    else:
        user_msg = "Look at this image and set the counter to the number of dots you see."
        print(f"User: {user_msg}")

        # This will include image_url in the OpenAI request
        intent = adapter.message_to_intent_or_plan(
            message=user_msg,
            history=[],
            state_snapshot={},
            component_registry={},
            action_registry={"demo.counter.set": set_action.model_dump()},
            media=media.model_dump(),
        )
        assert isinstance(intent, ChatIntent)
        print(
            f"Agent identified action: {intent.action_id} with inputs: {intent.inputs}"
        )

    # 3. Engine Execution and Media Hashing
    print("\n--- Phase 2: Engine Media Hashing ---")
    result = engine.execute_intent(project_id, intent)

    print(f"Status: {result.status}")
    print(f"Metadata: {result.metadata}")

    if "media_hash" in result.metadata:
        print(
            f"Verified: Media hashed and stored (Hash: {result.metadata['media_hash'][:16]}...)"
        )
        print(
            "Note: The original image data is NOT stored in the audit log to save space."
        )


if __name__ == "__main__":
    run_example()
