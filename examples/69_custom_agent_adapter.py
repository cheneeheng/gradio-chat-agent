"""Example of implementing a Custom Agent Adapter.

This example demonstrates how to:
1. Implement the AgentAdapter abstract base class.
2. Create a deterministic "KeywordAdapter" for testing or local use.
3. Use the custom adapter in the execution flow.
"""

from typing import Any, Optional, Union
import uuid

from gradio_chat_agent.chat.adapter import AgentAdapter
from gradio_chat_agent.models.enums import IntentType, ExecutionMode
from gradio_chat_agent.models.intent import ChatIntent
from gradio_chat_agent.models.plan import ExecutionPlan

class KeywordMockAdapter(AgentAdapter):
    """A simple adapter that maps keywords to actions without an LLM."""

    def message_to_intent_or_plan(
        self,
        message: str,
        history: list[dict[str, Any]],
        state_snapshot: dict[str, Any],
        component_registry: dict[str, Any],
        action_registry: dict[str, Any],
        media: Optional[dict[str, Any]] = None,
        execution_mode: str = "assisted",
        facts: Optional[dict[str, Any]] = None,
    ) -> Union[ChatIntent, ExecutionPlan]:
        
        msg = message.lower()
        
        # 1. Check for 'set counter' keyword
        if "set counter to" in msg:
            try:
                val = int(msg.split("to")[-1].strip())
                return ChatIntent(
                    type=IntentType.ACTION_CALL,
                    request_id=str(uuid.uuid4()),
                    action_id="demo.counter.set",
                    inputs={"value": val},
                    execution_mode=ExecutionMode(execution_mode)
                )
            except ValueError:
                pass

        # 2. Check for 'reset' keyword
        if "reset" in msg:
            return ChatIntent(
                type=IntentType.ACTION_CALL,
                request_id=str(uuid.uuid4()),
                action_id="demo.counter.reset",
                inputs={},
                execution_mode=ExecutionMode(execution_mode)
            )

        # 3. Fallback to clarification
        return ChatIntent(
            type=IntentType.CLARIFICATION_REQUEST,
            request_id=str(uuid.uuid4()),
            question="I didn't recognize any commands. Try 'set counter to 10' or 'reset'.",
            execution_mode=ExecutionMode(execution_mode)
        )

def run_example():
    # 1. Instantiate the custom adapter
    adapter = KeywordMockAdapter()
    
    print("--- Scenario 1: Successful Keyword Match ---")
    intent = adapter.message_to_intent_or_plan(
        message="Please set counter to 42",
        history=[],
        state_snapshot={},
        component_registry={},
        action_registry={}
    )
    print(f"Input: 'Please set counter to 42'")
    print(f"Proposes: {intent.action_id} with {intent.inputs}")

    print("\n--- Scenario 2: Clarification Fallback ---")
    intent2 = adapter.message_to_intent_or_plan(
        message="What time is it?",
        history=[],
        state_snapshot={},
        component_registry={},
        action_registry={}
    )
    print(f"Input: 'What time is it?'")
    print(f"Response: {intent2.question}")

if __name__ == "__main__":
    run_example()
