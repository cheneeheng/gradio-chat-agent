"""Utility functions for the Gradio Chat Agent.

This module provides shared helper functions used across the application,
such as diff computation and common transformations.
"""

from typing import Any

from gradio_chat_agent.models.enums import StateDiffOp
from gradio_chat_agent.models.execution_result import StateDiffEntry


def compute_state_diff(
    old_state: dict[str, Any], new_state: dict[str, Any], path_prefix: str = ""
) -> list[StateDiffEntry]:
    """Computes a simplified diff between two state dictionaries.

    This function recursively compares two dictionaries and generates a list of
    add, remove, or replace operations required to transform old_state into
    new_state.

    Args:
        old_state: The original state dictionary.
        new_state: The new state dictionary.
        path_prefix: Internal recursion helper to build dotted paths.
            Defaults to an empty string.

    Returns:
        A list of StateDiffEntry objects describing the changes between the
        two states.
    """
    diffs = []

    all_keys = set(old_state.keys()) | set(new_state.keys())

    for key in all_keys:
        path = f"{path_prefix}.{key}" if path_prefix else key

        if key not in old_state:
            diffs.append(
                StateDiffEntry(
                    path=path, op=StateDiffOp.ADD, value=new_state[key]
                )
            )
        elif key not in new_state:
            diffs.append(
                StateDiffEntry(path=path, op=StateDiffOp.REMOVE, value=None)
            )
        elif old_state[key] != new_state[key]:
            if isinstance(old_state[key], dict) and isinstance(
                new_state[key], dict
            ):
                diffs.extend(
                    compute_state_diff(old_state[key], new_state[key], path)
                )
            else:
                diffs.append(
                    StateDiffEntry(
                        path=path, op=StateDiffOp.REPLACE, value=new_state[key]
                    )
                )

    return diffs
