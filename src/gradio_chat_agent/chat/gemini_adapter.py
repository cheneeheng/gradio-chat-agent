"""Gemini-based implementation of the chat agent adapter.

This module provides an adapter that uses Google's Gemini models
(specifically with function calling) to translate user messages into structured
application intents or plans.
"""

import json
import os
import uuid
from typing import Any, Optional, Union

import google.generativeai as genai
from google.generativeai.types import BlobDict, FunctionDeclaration, Tool

from gradio_chat_agent.chat.adapter import AgentAdapter
from gradio_chat_agent.models.enums import ExecutionMode, IntentType
from gradio_chat_agent.models.intent import ChatIntent
from gradio_chat_agent.models.plan import ExecutionPlan
from gradio_chat_agent.observability.metrics import LLM_TOKEN_USAGE_TOTAL


class GeminiAgentAdapter(AgentAdapter):
    """Adapter for Google Gemini models that utilizes function calling."""

    def __init__(self, model_name: str = "gemini-2.0-flash"):
        """Initializes the Gemini adapter.

        Args:
            model_name: The identifier of the Gemini model to use.
                Defaults to 'gemini-2.0-flash' unless overridden by the
                GEMINI_MODEL environment variable.
        """
        api_key = os.environ.get("GOOGLE_API_KEY")
        if not api_key:
            # Fallback or warning could go here, but for now we assume it's set
            pass

        genai.configure(api_key=api_key)
        self.model_name = os.environ.get("GEMINI_MODEL", model_name)

    def _registry_to_tools(self, action_registry: dict[str, Any]) -> Tool:
        """Converts the action registry into Gemini tools format.

        Args:
            action_registry: Dictionary of available action declarations.

        Returns:
            A Gemini Tool object containing the function declarations.
        """
        function_declarations = []
        for action_id, action_def in action_registry.items():
            function_declarations.append(
                FunctionDeclaration(
                    name=action_id,
                    description=action_def.get("description", ""),
                    parameters=action_def.get("input_schema", {}),
                )
            )

        # Add built-in tool for clarification
        function_declarations.append(
            FunctionDeclaration(
                name="ask_clarification",
                description="Ask the user a clarifying question when the request is ambiguous or missing information.",
                parameters={
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
            )
        )

        return Tool(function_declarations=function_declarations)

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
        """Translates a user message into a structured intent using Gemini.

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
        # Prepare tools
        tools = self._registry_to_tools(action_registry)

        # Prepare system instruction
        system_instruction = self._construct_system_prompt(
            component_registry, state_snapshot, execution_mode, facts
        )

        # Initialize model
        model = genai.GenerativeModel(
            model_name=self.model_name,
            tools=[tools],
            system_instruction=system_instruction,
        )

        # Convert history to Gemini format
        chat_history = []
        for turn in history:
            role = turn.get("role", "user")
            content_text = str(turn.get("content", ""))

            # Map roles: 'assistant' -> 'model'
            gemini_role = "model" if role == "assistant" else "user"

            if role in ["user", "assistant"]:
                chat_history.append(
                    {"role": gemini_role, "parts": [content_text]}
                )

        # Add current user message
        user_parts = [message]
        if media:
            data = media.get("data")
            mime = media.get("mime_type")
            if data and mime:
                # construct blob
                blob: BlobDict = {"mime_type": mime, "data": data}
                user_parts.append(blob)

        try:
            # Start chat with history
            chat = model.start_chat(history=chat_history)

            # Send message
            response = chat.send_message(user_parts)

            # Extract function calls
            function_calls = []

            for part in response.parts:
                if fn := part.function_call:
                    function_calls.append(fn)

            # Metrics
            if response.usage_metadata:
                LLM_TOKEN_USAGE_TOTAL.labels(model=self.model_name).inc(
                    response.usage_metadata.total_token_count
                )

            if not function_calls:
                text_content = (
                    response.text or "I'm not sure what you want to do."
                )
                return ChatIntent(
                    type=IntentType.CLARIFICATION_REQUEST,
                    request_id=str(uuid.uuid4()),
                    question=text_content,
                    execution_mode=ExecutionMode(execution_mode),
                )

            intents = []
            for fn in function_calls:
                fn_name = fn.name
                arguments = dict(fn.args)

                if fn_name == "ask_clarification":
                    return ChatIntent(
                        type=IntentType.CLARIFICATION_REQUEST,
                        request_id=str(uuid.uuid4()),
                        question=arguments.get("question", "Can you clarify?"),
                        choices=arguments.get("choices", []),
                        execution_mode=ExecutionMode(execution_mode),
                    )

                # Check if action exists
                if fn_name not in action_registry:
                    return ChatIntent(
                        type=IntentType.CLARIFICATION_REQUEST,
                        request_id=str(uuid.uuid4()),
                        question=f"I tried to use an unknown action: {fn_name}",
                        execution_mode=ExecutionMode(execution_mode),
                    )

                intents.append(
                    ChatIntent(
                        type=IntentType.ACTION_CALL,
                        request_id=str(uuid.uuid4()),
                        action_id=fn_name,
                        inputs=arguments,
                        execution_mode=ExecutionMode(execution_mode),
                        confirmed=arguments.get("confirmed", False),
                    )
                )

            if len(intents) == 1:
                return intents[0]
            else:
                return ExecutionPlan(plan_id=str(uuid.uuid4()), steps=intents)

        except Exception as e:
            return ChatIntent(
                type=IntentType.CLARIFICATION_REQUEST,
                request_id=f"err_{uuid.uuid4()}",
                question=f"Error communicating with Gemini: {str(e)}",
                execution_mode=ExecutionMode(execution_mode),
            )
