import json
import os
from typing import Any, Optional, Union, cast

from openai import OpenAI
from pydantic import ValidationError

from gradio_chat_agent.chat.adapter import AgentAdapter
from gradio_chat_agent.models.enums import IntentType, ExecutionMode
from gradio_chat_agent.models.intent import ChatIntent
from gradio_chat_agent.models.plan import ExecutionPlan


class OpenAIAgentAdapter(AgentAdapter):
    """Adapter for OpenAI models."""

    def __init__(self, model_name: str = "gpt-4o-mini"):
        """Initialize the adapter.

        Args:
            model_name: The OpenAI model to use.
        """
        self.client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
        self.model_name = os.environ.get("OPENAI_MODEL", model_name)

    def _registry_to_tools(self, action_registry: dict[str, Any]) -> list[dict]:
        """Convert the action registry to OpenAI tools format."""
        tools = []
        for action_id, action_def in action_registry.items():
            # OpenAI function schema
            function_def = {
                "name": action_id,
                "description": action_def.get("description", ""),
                "parameters": action_def.get("input_schema", {}),
            }
            tools.append({"type": "function", "function": function_def})
        
        # Add built-in tool for clarification
        tools.append({
            "type": "function",
            "function": {
                "name": "ask_clarification",
                "description": "Ask the user a clarifying question when the request is ambiguous or missing information.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "question": {
                            "type": "string",
                            "description": "The question to ask the user."
                        },
                        "choices": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Optional list of choices for the user to pick from."
                        }
                    },
                    "required": ["question"]
                }
            }
        })

        return tools

    def _construct_system_prompt(
        self,
        component_registry: dict[str, Any],
        state_snapshot: dict[str, Any],
        execution_mode: str
    ) -> str:
        """Construct the system prompt with context."""
        
        # Simplify component registry for context (reduce tokens)
        components_summary = {}
        for comp_id, comp_def in component_registry.items():
            components_summary[comp_id] = {
                "description": comp_def.get("description", ""),
                "permissions": comp_def.get("permissions", {})
            }

        prompt = f"""You are a governed execution agent.
Your goal is to help the user control the application state by proposing actions.

EXECUTION MODE: {execution_mode.upper()}

RULES:
1. You DO NOT execute actions directly. You propose them by calling the corresponding function.
2. You must rely on the provided Component Registry and Action Registry.
3. You must inspect the Current State before proposing an action (check preconditions).
4. If a request is ambiguous or missing parameters, use 'ask_clarification'.
5. Do not hallucinate action IDs. Only use the tools provided.

COMPONENT REGISTRY:
{json.dumps(components_summary, indent=2)}

CURRENT STATE SNAPSHOT:
{json.dumps(state_snapshot, indent=2)}
"""
        return prompt

    def message_to_intent_or_plan(
        self,
        message: str,
        history: list[dict[str, Any]],
        state_snapshot: dict[str, Any],
        component_registry: dict[str, Any],
        action_registry: dict[str, Any],
        media: Optional[dict[str, Any]] = None,
        execution_mode: str = "assisted"
    ) -> Union[ChatIntent, ExecutionPlan]:
        
        tools = self._registry_to_tools(action_registry)
        system_prompt = self._construct_system_prompt(component_registry, state_snapshot, execution_mode)

        messages = [{"role": "system", "content": system_prompt}]
        
        # Add history
        # Assuming history is list of dicts with role/content compatible with OpenAI
        # We might need to filter or adapt generic history if it contains non-OpenAI fields
        # For now, we assume simple text history.
        for turn in history:
            messages.append({
                "role": turn.get("role", "user"),
                "content": str(turn.get("content", ""))
            })
            
        # Add current user message
        user_content = [{"type": "text", "text": message}]
        if media:
             # TODO: Handle media if needed, for now just text
             pass
             
        messages.append({"role": "user", "content": user_content})

        try:
            completion = self.client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                tools=tools,
                tool_choice="auto" 
            )
        except Exception as e:
            # Fallback for errors
            return ChatIntent(
                type=IntentType.CLARIFICATION_REQUEST,
                request_id=f"err_{id(messages)}",
                question=f"Error communicating with LLM: {str(e)}",
                execution_mode=ExecutionMode(execution_mode)
            )

        message_output = completion.choices[0].message
        tool_calls = message_output.tool_calls

        # Generate a request ID (in a real app, use UUID)
        import uuid
        req_id = str(uuid.uuid4())

        if tool_calls:
            # For now, handle the first tool call as the intent
            # TODO: Support Multi-step plans (ExecutionPlan) if multiple tools are called 
            # or if a specific 'propose_plan' tool is used.
            
            tool_call = tool_calls[0]
            function_name = tool_call.function.name
            try:
                arguments = json.loads(tool_call.function.arguments)
            except json.JSONDecodeError:
                arguments = {}

            if function_name == "ask_clarification":
                return ChatIntent(
                    type=IntentType.CLARIFICATION_REQUEST,
                    request_id=req_id,
                    question=arguments.get("question", "Can you clarify?"),
                    choices=arguments.get("choices", []),
                    execution_mode=ExecutionMode(execution_mode)
                )
            
            # Otherwise it's an action call
            return ChatIntent(
                type=IntentType.ACTION_CALL,
                request_id=req_id,
                action_id=function_name,
                inputs=arguments,
                execution_mode=ExecutionMode(execution_mode)
            )
        
        # If no tool called, treat content as clarification or chatter
        content = message_output.content or "I'm not sure what you want to do."
        return ChatIntent(
            type=IntentType.CLARIFICATION_REQUEST,
            request_id=req_id,
            question=content,
            execution_mode=ExecutionMode(execution_mode)
        )
