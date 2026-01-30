"""Abstract base classes for chat agent adapters.

This module defines the interface that all chat agent adapters must implement
to translate user messages and application state into structured intents
or multi-step execution plans.
"""

from abc import ABC, abstractmethod
from typing import Any, Optional, Union

from gradio_chat_agent.models.intent import ChatIntent
from gradio_chat_agent.models.plan import ExecutionPlan


class AgentAdapter(ABC):
    """Abstract base class for LLM agent adapters.

    This interface defines how the application interacts with an LLM to convert
    natural language and context into structured intents or plans.
    """

    @abstractmethod
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
        """Converts a user message and context into a structured intent or plan.

        Args:
            message: Raw text from user.
            history: List of past conversation turns. Each turn is typically a
                dictionary with 'role' and 'content' keys.
            state_snapshot: Current project state snapshot as a JSON-serializable
                dictionary.
            component_registry: Dictionary of all available components and their
                declarations.
            action_registry: Dictionary of all available actions and their
                declarations.
            media: Optional multimodal data such as image or document data.
                Defaults to None.
            execution_mode: The operational mode for agent execution (e.g.,
                'interactive', 'assisted', 'autonomous'). Defaults to 'assisted'.
            facts: Dictionary of session facts (memory) to provide context.

        Returns:
            A ChatIntent object representing a single action or clarification
            request, or an ExecutionPlan representing a sequence of actions.
        """
        pass  # pragma: no cover
