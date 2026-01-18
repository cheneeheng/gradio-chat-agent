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
        """Initializes an empty in-memory registry."""
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
        """Registers a new action and its associated handler.

        Args:
            action: The action declaration object to register.
            handler: The function to be called when this action is executed.
        """
        self._actions[action.action_id] = action
        self._handlers[action.action_id] = handler

    def _get_latest_version(self, base_id: str, store: dict) -> Optional[str]:
        """Finds the latest version of a component or action.

        Args:
            base_id: The identifier without the version suffix.
            store: The dictionary to search in (_components or _actions).

        Returns:
            The full identifier of the latest version, or None if not found.
        """
        if base_id in store:
            return base_id

        # Look for matches with @ suffix
        matches = [k for k in store.keys() if k.startswith(f"{base_id}@")]
        if not matches:
            return None

        # Sort matches and pick the last one (e.g., v2 > v1)
        return sorted(matches)[-1]

    def get_component(
        self, component_id: str
    ) -> Optional[ComponentDeclaration]:
        """Retrieves a component declaration by its ID.

        If no version is specified, returns the latest version.

        Args:
            component_id: The unique dot-notation identifier of the component.

        Returns:
            The component declaration if found, otherwise None.
        """
        if "@" in component_id:
            return self._components.get(component_id)

        latest_id = self._get_latest_version(component_id, self._components)
        return self._components.get(latest_id) if latest_id else None

    def list_components(self) -> list[ComponentDeclaration]:
        """Lists all registered components in the registry.

        Returns:
            A list of all component declarations currently in the registry.
        """
        return list(self._components.values())

    def get_action(self, action_id: str) -> Optional[ActionDeclaration]:
        """Retrieves an action declaration by its ID.

        If no version is specified, returns the latest version.

        Args:
            action_id: The unique dot-notation identifier of the action.

        Returns:
            The action declaration if found, otherwise None.
        """
        if "@" in action_id:
            return self._actions.get(action_id)

        latest_id = self._get_latest_version(action_id, self._actions)
        return self._actions.get(latest_id) if latest_id else None

    def list_actions(self) -> list[ActionDeclaration]:
        """Lists all registered actions in the registry.

        Returns:
            A list of all action declarations currently in the registry.
        """
        return list(self._actions.values())

    def get_handler(self, action_id: str) -> Optional[Callable]:
        """Retrieves the executable handler function for an action.

        If no version is specified, returns the handler for the latest version.

        Args:
            action_id: The unique identifier of the action.

        Returns:
            The callable handler function if found, otherwise None.
        """
        if "@" in action_id:
            return self._handlers.get(action_id)

        latest_id = self._get_latest_version(action_id, self._actions)
        return self._handlers.get(latest_id) if latest_id else None
