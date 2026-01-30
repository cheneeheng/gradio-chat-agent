"""Declarative UI binding for the Gradio Chat Agent.

This module provides utilities to bind Gradio components directly to paths
in the application state, ensuring that UI updates are a pure function
of the central state.
"""

from typing import Any, Callable, Optional

import gradio as gr


class UIBinder:
    """Manages bindings between Gradio components and state paths."""

    def __init__(self):
        # List of (path, component, update_fn)
        self.bindings: list[tuple[str, gr.Component, Optional[Callable]]] = []

    def bind(
        self,
        path: str,
        component: gr.Component,
        update_fn: Optional[Callable] = None,
    ):
        """Binds a component to a state path.

        Args:
            path: Dot-notation path in the state (e.g., 'demo.counter.value').
            component: The Gradio component instance.
            update_fn: Optional custom function to transform state value to component value.
                Signature: (value) -> any
        """
        self.bindings.append((path, component, update_fn))

    def _get_value_at_path(self, state: dict[str, Any], path: str) -> Any:
        """Retrieves a value from a nested dictionary using a dot-notation path."""
        parts = path.split(".")
        current = state
        for part in parts:
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                return None
        return current

    def get_updates(self, state: dict[str, Any]) -> list[Any]:
        """Generates a list of gr.update() calls for all bound components.

        Args:
            state: The full application state dictionary.

        Returns:
            A list of gr.update() results in the order components were registered.
        """
        updates = []
        for path, component, update_fn in self.bindings:
            val = self._get_value_at_path(state, path)
            if val is not None:
                if update_fn:
                    val = update_fn(val)
                updates.append(gr.update(value=val))
            else:
                # If path doesn't exist, we might want to keep current or clear it
                updates.append(gr.update())
        return updates

    def get_bound_components(self) -> list[gr.Component]:
        """Returns the list of Gradio component instances that are bound."""
        return [b[1] for b in self.bindings]
