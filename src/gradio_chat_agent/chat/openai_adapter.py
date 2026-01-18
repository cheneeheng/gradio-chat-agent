"""OpenAI-based implementation of the chat agent adapter.

This module provides an adapter that uses OpenAI's Chat Completion API
(specifically tool calling) to translate user messages into structured
application intents or plans.
"""

import json
import os
import uuid
from typing import Any, Optional, Union, cast

from openai import OpenAI
from openai.types.chat.chat_completion_content_part_param import (
    ChatCompletionContentPartParam,
)
from openai.types.chat.chat_completion_function_tool_param import (
    ChatCompletionFunctionToolParam,
)
from openai.types.chat.chat_completion_message import (
    ChatCompletionMessage,
)
from openai.types.chat.chat_completion_message_function_tool_call import (
    ChatCompletionMessageFunctionToolCall,
)
from openai.types.chat.chat_completion_message_param import (
    ChatCompletionMessageParam,
)
from openai.types.shared_params.function_definition import FunctionDefinition

from gradio_chat_agent.chat.adapter import AgentAdapter
from gradio_chat_agent.models.enums import ExecutionMode, IntentType
from gradio_chat_agent.models.intent import ChatIntent
from gradio_chat_agent.models.plan import ExecutionPlan
from gradio_chat_agent.observability.metrics import LLM_TOKEN_USAGE_TOTAL


class OpenAIAgentAdapter(AgentAdapter):
    """Adapter for OpenAI models that utilizes function calling."""

    def __init__(self, model_name: str = "gpt-4o-mini"):
        """Initializes the OpenAI adapter.

        Args:
            model_name: The identifier of the OpenAI model to use.
                Defaults to 'gpt-4o-mini' unless overridden by the
                OPENAI_MODEL environment variable.
        """
        api_key = os.environ.get("OPENAI_API_KEY")
        base_url = os.environ.get("OPENAI_API_BASE")

        self.client = OpenAI(api_key=api_key, base_url=base_url)
        self.model_name = os.environ.get("OPENAI_MODEL", model_name)

    def _registry_to_tools(
        self, action_registry: dict[str, Any]
    ) -> list[ChatCompletionFunctionToolParam]:
        """Converts the action registry into OpenAI tools format.

        Args:
            action_registry: Dictionary of available action declarations.

        Returns:
            A list of dictionary objects representing OpenAI tool definitions.
        """
        tools: list[ChatCompletionFunctionToolParam] = []
        for action_id, action_def in action_registry.items():
            # OpenAI function schema
            function_def: FunctionDefinition = {
                "name": action_id,
                "description": action_def.get("description", ""),
                "parameters": action_def.get("input_schema", {}),
            }
            tools.append({"type": "function", "function": function_def})

        # Add built-in tool for clarification
        tools.append(
            {
                "type": "function",
                "function": {
                    "name": "ask_clarification",
                    "description": "Ask the user a clarifying question when the request is ambiguous or missing information.",  # noqa: E501
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "question": {
                                "type": "string",
                                "description": "The question to ask the user.",
                            },
                            "choices": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Optional list of choices for the user to pick from.",
                            },
                        },
                        "required": ["question"],
                    },
                },
            }
        )

        return tools

    def _construct_system_prompt(
        self,
        component_registry: dict[str, Any],
        state_snapshot: dict[str, Any],
        execution_mode: str,
        facts: Optional[dict[str, Any]] = None,
    ) -> str:
        """Constructs the system prompt with context for the LLM.

        Args:
            component_registry: Dictionary of available components.
            state_snapshot: Current state of all application components.
            execution_mode: The active operational mode.
            facts: Optional dictionary of session facts.

        Returns:
            A string containing the formatted system prompt.
        """

        # Simplify component registry for context (reduce tokens)
        components_summary = {}
        for comp_id, comp_def in component_registry.items():
            components_summary[comp_id] = {
                "description": comp_def.get("description", ""),
                "permissions": comp_def.get("permissions", {}),
                "invariants": comp_def.get("invariants", []),
            }

        facts_str = (
            json.dumps(facts, indent=2) if facts else "No facts stored."
        )

        prompt = f"""You are a governed execution agent.
Your goal is to help the user control the application state by proposing actions.

EXECUTION MODE: {execution_mode.upper()}

RULES:
1. You DO NOT execute actions directly. You propose them by calling the corresponding function.
2. You must rely on the provided Component Registry and Action Registry.
3. You must inspect the Current State before proposing an action (check preconditions).
   - If an action requires specific state (e.g., 'loaded=true') and it is not met, DO NOT propose it.
   - Instead, propose the minimal prerequisite action first.
4. If a request is ambiguous or missing parameters:
   - Use 'ask_clarification'.
   - Present a list of 'choices' if multiple actions match.
   - Only ask for the specific missing required parameters defined in the schema.
5. Do not hallucinate action IDs. Only use the tools provided.
6. If the user confirms a previous request (e.g., "yes", "proceed"), re-submit the action with the same parameters.

COMPONENT REGISTRY:
{json.dumps(components_summary, indent=2)}

CURRENT STATE SNAPSHOT:
{json.dumps(state_snapshot, indent=2)}

SESSION MEMORY (FACTS):
{facts_str}
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
        execution_mode: str = "assisted",
        facts: Optional[dict[str, Any]] = None,
    ) -> Union[ChatIntent, ExecutionPlan]:
        """Translates a user message into a structured intent using OpenAI.

        Args:
            message: Raw text from user.
            history: List of past conversation turns.
            state_snapshot: Current project state snapshot.
            component_registry: Dict of available components.
            action_registry: Dict of available actions.
            media: Optional image/document data. Defaults to None.
            execution_mode: Current execution mode. Defaults to 'assisted'.
            facts: Optional session facts.

        Returns:
            A ChatIntent or ExecutionPlan object.
        """

        tools: list[ChatCompletionFunctionToolParam] = self._registry_to_tools(
            action_registry
        )
        system_prompt = self._construct_system_prompt(
            component_registry, state_snapshot, execution_mode, facts
        )

        messages: list[ChatCompletionMessageParam] = [
            {"role": "system", "content": system_prompt}
        ]

        for turn in history:
            messages.append(
                {
                    "role": turn.get("role", "user"),
                    "content": str(turn.get("content", "")),
                }
            )

        # Add current user message
        user_content: list[ChatCompletionContentPartParam] = [
            {"type": "text", "text": message}
        ]
        if media:
            data = media.get("data")
            mime = media.get("mime_type")
            if data and mime:
                url = f"data:{mime};base64,{data}"
                user_content.append(
                    {
                        "type": "image_url",
                        "image_url": {"url": url},
                    }
                )

        messages.append({"role": "user", "content": user_content})

        # Make sure that the variables are bounded
        tool_calls = []
        message_output = ChatCompletionMessage(role="assistant")

        max_retries = 2
        for attempt in range(max_retries + 1):
            try:
                completion = self.client.chat.completions.create(
                    model=self.model_name,
                    messages=messages,
                    tools=tools,
                    tool_choice="auto",
                )
            except Exception as e:
                # Fallback for errors
                return ChatIntent(
                    type=IntentType.CLARIFICATION_REQUEST,
                    request_id=f"err_{id(messages)}",
                    question=f"Error communicating with LLM: {str(e)}",
                    execution_mode=ExecutionMode(execution_mode),
                )

            message_output = completion.choices[0].message
            tool_calls = message_output.tool_calls or []

            # Metrics
            if hasattr(completion, "usage") and completion.usage:
                LLM_TOKEN_USAGE_TOTAL.labels(model=self.model_name).inc(
                    completion.usage.total_tokens
                )

            # Check for hallucinations
            invalid_tools = []
            for tc in tool_calls:
                tc = cast(ChatCompletionMessageFunctionToolCall, tc)
                fn_name = tc.function.name
                if (
                    fn_name != "ask_clarification"
                    and fn_name not in action_registry
                ):
                    invalid_tools.append(fn_name)

            if invalid_tools and attempt < max_retries:
                # Append assistant message with bad calls
                messages.append(
                    cast(
                        ChatCompletionMessageParam, message_output.model_dump()
                    )
                )
                # Append tool error outputs
                for tc in tool_calls:
                    tc = cast(ChatCompletionMessageFunctionToolCall, tc)
                    fn_name = tc.function.name
                    content = (
                        f"Error: Action '{fn_name}' does not exist."
                        if fn_name in invalid_tools
                        else "Action suppressed due to batch error."
                    )
                    messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": tc.id,
                            "content": content,
                        }
                    )
                continue

            # If valid or max retries reached, proceed
            break

        if not tool_calls:
            content = (
                message_output.content or "I'm not sure what you want to do."
            )
            return ChatIntent(
                type=IntentType.CLARIFICATION_REQUEST,
                request_id=str(uuid.uuid4()),
                question=content,
                execution_mode=ExecutionMode(execution_mode),
            )

        intents = []
        for tc in tool_calls:
            tc = cast(ChatCompletionMessageFunctionToolCall, tc)
            fn_name = tc.function.name
            try:
                arguments = json.loads(tc.function.arguments)
            except json.JSONDecodeError:
                arguments = {}

            if fn_name == "ask_clarification":
                return ChatIntent(
                    type=IntentType.CLARIFICATION_REQUEST,
                    request_id=str(uuid.uuid4()),
                    question=arguments.get("question", "Can you clarify?"),
                    choices=arguments.get("choices", []),
                    execution_mode=ExecutionMode(execution_mode),
                )

            # Action Intent
            # Check for confirmation heuristic if arguments missing confirmation?
            # Actually, System Prompt Rule 6 says LLM should re-submit with parameters.
            # So we assume arguments contains 'confirmed=True' if LLM did its job.

            intents.append(
                ChatIntent(
                    type=IntentType.ACTION_CALL,
                    request_id=str(uuid.uuid4()),
                    action_id=fn_name,
                    inputs=arguments,
                    execution_mode=ExecutionMode(execution_mode),
                    confirmed=arguments.get("confirmed", False),  # Trust LLM
                )
            )

        if len(intents) == 1:
            return intents[0]
        else:
            return ExecutionPlan(plan_id=str(uuid.uuid4()), steps=intents)
