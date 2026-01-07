"""In-memory implementation of the Registry interface.

This module provides a simple dictionary-backed registry for development,
testing, and single-instance deployments.
"""

from typing import Callable, Optional

from gradio_chat_agent.models.action import ActionDeclaration
from gradio_chat_agent.models.component import ComponentDeclaration
from gradio_chat_agent.registry.abstract import Registry


class InMemoryRegistry(Registry):
    """A thread-safe, in-memory registry for components and actions."""

    def __init__(self):
        """Initializes an empty registry."""
        self._components: dict[str, ComponentDeclaration] = {}
        self._actions: dict[str, ActionDeclaration] = {}
        self._handlers: dict[str, Callable] = {}

    def register_component(self, component: ComponentDeclaration):
        """Registers a new component declaration.

        Args:
            component: The component declaration object to register.
        """
        self._components[component.component_id] = component

    def register_action(self, action: ActionDeclaration, handler: Callable):
        """Registers a new action and its handler.

        Args:
            action: The action declaration object.
            handler: The function to call when this action is executed.
        """
        self._actions[action.action_id] = action
        self._handlers[action.action_id] = handler

    def get_component(
        self, component_id: str
    ) -> Optional[ComponentDeclaration]:
        """Retrieves a component by ID.

        Args:
            component_id: The ID of the component to find.

        Returns:
            The component declaration, or None if not found.
        """
        return self._components.get(component_id)

    def list_components(self) -> list[ComponentDeclaration]:
        """Lists all registered components.

        Returns:
            A list of component declarations.
        """
        return list(self._components.values())

    def get_action(self, action_id: str) -> Optional[ActionDeclaration]:
        """Retrieves an action by ID.

        Args:
            action_id: The ID of the action to find.

        Returns:
            The action declaration, or None if not found.
        """
        return self._actions.get(action_id)

    def list_actions(self) -> list[ActionDeclaration]:
        """Lists all registered actions.

        Returns:
            A list of action declarations.
        """
        return list(self._actions.values())

    def get_handler(self, action_id: str) -> Optional[Callable]:
        """Retrieves the handler for an action.

        Args:
            action_id: The ID of the action.

        Returns:
            The callable handler, or None if not found.
        """
        return self._handlers.get(action_id)