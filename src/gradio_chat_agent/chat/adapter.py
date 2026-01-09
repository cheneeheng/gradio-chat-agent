from abc import ABC, abstractmethod
from typing import Union, Optional, Any

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
        execution_mode: str = "assisted"
    ) -> Union[ChatIntent, ExecutionPlan]:
        """
        Converts a user message and context into a structured intent or plan.

        Args:
            message: Raw text from user.
            history: List of past conversation turns.
            state_snapshot: Current project state snapshot (JSON/Dict).
            component_registry: Dict of available components.
            action_registry: Dict of available actions.
            media: Optional image/document data.
            execution_mode: Current execution mode (interactive, assisted, autonomous).

        Returns:
            A ChatIntent (single action/question) or ExecutionPlan (multi-step).
        """
        pass  # pragma: no cover
