"""Enumeration definitions for the Gradio Chat Agent.

This module contains standard Enum classes used across the application to ensure
consistency in typing and values for intents, execution modes, statuses,
and configuration options.
"""

from enum import Enum


class IntentType(str, Enum):
    """Defines the type of intent expressed by the agent.

    Attributes:
        ACTION_CALL: The agent wants to execute a specific action.
        CLARIFICATION_REQUEST: The agent needs more information from the user.
    """

    ACTION_CALL = "action_call"
    CLARIFICATION_REQUEST = "clarification_request"


class ExecutionMode(str, Enum):
    """Defines the operational mode for the agent execution.

    Attributes:
        INTERACTIVE: Maximizes user control; stops for confirmation often.
        ASSISTED: Balances automation and control; may plan ahead.
        AUTONOMOUS: Optimizes for speed; runs until completion or limit.
    """

    INTERACTIVE = "interactive"
    ASSISTED = "assisted"
    AUTONOMOUS = "autonomous"


class MediaType(str, Enum):
    """Defines supported media types for multimodal intents.

    Attributes:
        IMAGE: Static image content.
        DOCUMENT: Text or PDF document content.
    """

    IMAGE = "image"
    DOCUMENT = "document"


class ExecutionStatus(str, Enum):
    """Defines the final status of an execution attempt.

    Attributes:
        SUCCESS: The action completed and state was updated.
        REJECTED: The action was blocked by policy, validation, or permission.
        FAILED: The action handler raised an exception during execution.
    """

    SUCCESS = "success"
    REJECTED = "rejected"
    FAILED = "failed"


class StateDiffOp(str, Enum):
    """Defines the type of operation in a state diff entry.

    Attributes:
        ADD: A new key or item was added.
        REMOVE: An existing key or item was removed.
        REPLACE: An existing value was changed.
    """

    ADD = "add"
    REMOVE = "remove"
    REPLACE = "replace"


class ActionRisk(str, Enum):
    """Defines the risk level associated with an action.

    Attributes:
        LOW: Safe, reversible, or trivial actions.
        MEDIUM: Actions with side effects or moderate cost.
        HIGH: Destructive or sensitive actions requiring strict confirmation.
    """

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class ActionVisibility(str, Enum):
    """Defines who can see and invoke an action.

    Attributes:
        USER: Visible to end-users in the UI.
        DEVELOPER: Hidden from standard UI, used for debugging or system tasks.
    """

    USER = "user"
    DEVELOPER = "developer"