"""Persistence layer interfaces and implementations.

This module defines the abstract contract for state persistence.
"""

from abc import ABC, abstractmethod
from typing import Any, Optional

from gradio_chat_agent.models.execution_result import (
    ExecutionResult,
)
from gradio_chat_agent.models.state_snapshot import StateSnapshot


class StateRepository(ABC):
    """Abstract interface for persisting application state and history."""

    @abstractmethod
    def get_latest_snapshot(self, project_id: str) -> Optional[StateSnapshot]:
        """Retrieves the most recent state snapshot for a project.

        Args:
            project_id: The ID of the project to retrieve the snapshot for.

        Returns:
            The latest StateSnapshot, or None if the project has no history.
        """
        pass  # pragma: no cover

    @abstractmethod
    def get_snapshot(self, snapshot_id: str) -> Optional[StateSnapshot]:
        """Retrieves a specific state snapshot by ID.

        Args:
            snapshot_id: The unique ID of the snapshot.

        Returns:
            The StateSnapshot if found, otherwise None.
        """
        pass  # pragma: no cover

    @abstractmethod
    def save_snapshot(self, project_id: str, snapshot: StateSnapshot):
        """Persists a new state snapshot.

        Args:
            project_id: The ID of the project to save the snapshot for.
            snapshot: The snapshot object to persist.
        """
        pass  # pragma: no cover

    @abstractmethod
    def save_execution(self, project_id: str, result: ExecutionResult):
        """Persists an execution result (audit log entry).

        Args:
            project_id: The ID of the project the execution belongs to.
            result: The execution result object to persist.
        """
        pass  # pragma: no cover

    @abstractmethod
    def get_execution_history(
        self, project_id: str, limit: int = 100
    ) -> list[ExecutionResult]:
        """Retrieves the recent execution history for a project.

        Args:
            project_id: The ID of the project to retrieve history for.
            limit: Maximum number of records to return. Defaults to 100.

        Returns:
            A list of ExecutionResult objects, ordered by timestamp descending.
        """
        pass  # pragma: no cover

    @abstractmethod
    def get_session_facts(
        self, project_id: str, user_id: str
    ) -> dict[str, Any]:
        """Retrieves all session facts for a specific user and project.

        Args:
            project_id: The ID of the project.
            user_id: The ID of the user.

        Returns:
            A dictionary of key-value facts stored for this user and project.
        """
        pass  # pragma: no cover

    @abstractmethod
    def save_session_fact(
        self, project_id: str, user_id: str, key: str, value: Any
    ):
        """Saves or updates a session fact.

        Args:
            project_id: The ID of the project.
            user_id: The ID of the user.
            key: The unique key for the fact.
            value: The value to store for the fact.
        """
        pass  # pragma: no cover

    @abstractmethod
    def delete_session_fact(self, project_id: str, user_id: str, key: str):
        """Deletes a session fact.

        Args:
            project_id: The ID of the project.
            user_id: The ID of the user.
            key: The key of the fact to remove.
        """
        pass  # pragma: no cover

    @abstractmethod
    def get_project_limits(self, project_id: str) -> dict[str, Any]:
        """Retrieves project limits and policy.

        Args:
            project_id: The ID of the project to retrieve limits for.

        Returns:
            A dictionary containing limit configuration and governance policies.
        """
        pass  # pragma: no cover

    @abstractmethod
    def set_project_limits(self, project_id: str, policy: dict[str, Any]):
        """Sets project limits.

        Args:
            project_id: The ID of the project to update limits for.
            policy: The policy dictionary containing limits configuration.
        """
        pass  # pragma: no cover

    @abstractmethod
    def count_recent_executions(self, project_id: str, minutes: int) -> int:
        """Counts successful executions in the last N minutes.

        Args:
            project_id: The ID of the project to count executions for.
            minutes: The lookback time window in minutes.

        Returns:
            The number of successful executions found in the specified window.
        """

        pass  # pragma: no cover

    @abstractmethod
    def get_webhook(self, webhook_id: str) -> Optional[dict[str, Any]]:
        """Retrieves a webhook configuration by ID.

        Args:
            webhook_id: The unique identifier of the webhook.

        Returns:
            A dictionary containing webhook details (id, project_id, action_id,
                secret, template).
        """

        pass  # pragma: no cover
