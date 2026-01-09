"""Abstract base class for the Component and Action Registry.

This module defines the interface for storing and retrieving definitions of
components and actions, as well as the executable handlers for actions.
"""

from abc import ABC, abstractmethod
from typing import Callable, Optional

from gradio_chat_agent.models.action import ActionDeclaration
from gradio_chat_agent.models.component import ComponentDeclaration


class Registry(ABC):
    """Interface for accessing component and action definitions."""

    @abstractmethod
    def get_component(
        self, component_id: str
    ) -> Optional[ComponentDeclaration]:
        """Retrieves a component declaration by its ID.

        Args:
            component_id: The unique dot-notation identifier of the component.

        Returns:
            The component declaration if found, otherwise None.
        """
        pass  # pragma: no cover

    @abstractmethod
    def list_components(self) -> list[ComponentDeclaration]:
        """Lists all registered components.

        Returns:
            A list of all component declarations in the registry.
        """
        pass  # pragma: no cover

    @abstractmethod
    def get_action(self, action_id: str) -> Optional[ActionDeclaration]:
        """Retrieves an action declaration by its ID.

        Args:
            action_id: The unique dot-notation identifier of the action.

        Returns:
            The action declaration if found, otherwise None.
        """
        pass  # pragma: no cover

    @abstractmethod
    def list_actions(self) -> list[ActionDeclaration]:
        """Lists all registered actions.

        Returns:
            A list of all action declarations in the registry.
        """
        pass  # pragma: no cover

    @abstractmethod
    def get_handler(self, action_id: str) -> Optional[Callable]:
        """Retrieves the executable handler function for an action.

        Args:
            action_id: The unique identifier of the action.

        Returns:
            The callable handler function if found, otherwise None.
        """
        pass  # pragma: no cover
