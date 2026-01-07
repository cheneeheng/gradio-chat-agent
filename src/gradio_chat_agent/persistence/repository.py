"""Persistence layer interfaces and implementations.

This module defines the abstract contract for state persistence and provides
a reference in-memory implementation for testing and ephemeral use cases.
"""

from abc import ABC, abstractmethod
from typing import Optional

from gradio_chat_agent.models.execution_result import ExecutionResult
from gradio_chat_agent.models.state_snapshot import StateSnapshot


class StateRepository(ABC):
    """Abstract interface for persisting application state and history."""

    @abstractmethod
    def get_latest_snapshot(self, project_id: str) -> Optional[StateSnapshot]:
        """Retrieves the most recent state snapshot for a project.

        Args:
            project_id: The ID of the project.

        Returns:
            The latest StateSnapshot, or None if the project has no history.
        """
        pass  # pragma: no cover

    @abstractmethod
    def save_snapshot(self, project_id: str, snapshot: StateSnapshot):
        """Persists a new state snapshot.

        Args:
            project_id: The ID of the project.
            snapshot: The snapshot object to save.
        """
        pass  # pragma: no cover

    @abstractmethod
    def save_execution(self, project_id: str, result: ExecutionResult):
        """Persists an execution result (audit log entry).

        Args:
            project_id: The ID of the project.
            result: The execution result to save.
        """
        pass  # pragma: no cover

    @abstractmethod
    def get_execution_history(
        self, project_id: str, limit: int = 100
    ) -> list[ExecutionResult]:
        """Retrieves the recent execution history for a project.

        Args:
            project_id: The ID of the project.
            limit: Maximum number of records to return.

        Returns:
            A list of ExecutionResult objects, ordered by timestamp descending.
        """
        pass  # pragma: no cover


class InMemoryStateRepository(StateRepository):
    """In-memory implementation of the StateRepository.

    Useful for unit tests and local development where persistence across
    restarts is not required.
    """

    def __init__(self):
        """Initializes the empty in-memory stores."""
        self._snapshots: dict[str, list[StateSnapshot]] = {}
        self._executions: dict[str, list[ExecutionResult]] = {}

    def get_latest_snapshot(self, project_id: str) -> Optional[StateSnapshot]:
        """Retrieves the most recent state snapshot for a project.

        Args:
            project_id: The ID of the project.

        Returns:
            The latest StateSnapshot, or None if not found.
        """
        snapshots = self._snapshots.get(project_id, [])
        if not snapshots:
            return None
        # Assuming last appended is latest
        return snapshots[-1]

    def save_snapshot(self, project_id: str, snapshot: StateSnapshot):
        """Persists a new state snapshot to the in-memory list.

        Args:
            project_id: The ID of the project.
            snapshot: The snapshot object to save.
        """
        if project_id not in self._snapshots:
            self._snapshots[project_id] = []
        self._snapshots[project_id].append(snapshot)

    def save_execution(self, project_id: str, result: ExecutionResult):
        """Persists an execution result to the in-memory list.

        Args:
            project_id: The ID of the project.
            result: The execution result to save.
        """
        if project_id not in self._executions:
            self._executions[project_id] = []
        self._executions[project_id].append(result)

    def get_execution_history(
        self, project_id: str, limit: int = 100
    ) -> list[ExecutionResult]:
        """Retrieves the recent execution history.

        Args:
            project_id: The ID of the project.
            limit: Maximum number of records to return.

        Returns:
            A list of ExecutionResult objects, newest first.
        """
        history = self._executions.get(project_id, [])
        return sorted(history, key=lambda x: x.timestamp, reverse=True)[:limit]