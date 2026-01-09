"""Persistence layer interfaces and implementations.

This module defines the abstract contract for state persistence and provides
a reference in-memory implementation for testing and ephemeral use cases.
"""

from abc import ABC, abstractmethod
from datetime import datetime, timedelta, timezone
from typing import Optional, Any

from gradio_chat_agent.models.execution_result import ExecutionResult, ExecutionStatus
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

    @abstractmethod
    def get_session_facts(self, project_id: str, user_id: str) -> dict[str, Any]:
        """Retrieves all session facts for a specific user and project.

        Args:
            project_id: The ID of the project.
            user_id: The ID of the user.

        Returns:
            A dictionary of key-value facts.
        """
        pass  # pragma: no cover

    @abstractmethod
    def save_session_fact(self, project_id: str, user_id: str, key: str, value: Any):
        """Saves or updates a session fact.

        Args:
            project_id: The ID of the project.
            user_id: The ID of the user.
            key: The fact key.
            value: The fact value.
        """
        pass  # pragma: no cover

    @abstractmethod
    def delete_session_fact(self, project_id: str, user_id: str, key: str):
        """Deletes a session fact.

        Args:
            project_id: The ID of the project.
            user_id: The ID of the user.
            key: The fact key.
        """
        pass  # pragma: no cover

    @abstractmethod
    def get_project_limits(self, project_id: str) -> dict[str, Any]:
        """Retrieves project limits and policy.

        Args:
            project_id: The ID of the project.

        Returns:
            A dictionary containing limit configuration.
        """
        pass  # pragma: no cover

    @abstractmethod
    def set_project_limits(self, project_id: str, limits: dict[str, Any]):
        """Sets project limits.

        Args:
            project_id: The ID of the project.
            limits: The limits dictionary.
        """
        pass  # pragma: no cover

    @abstractmethod
    def count_recent_executions(self, project_id: str, minutes: int) -> int:
        """Counts successful executions in the last N minutes.

        Args:
            project_id: The ID of the project.
            minutes: The time window in minutes.

        Returns:
            Count of executions.
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
        self._facts: dict[str, dict[str, Any]] = {}  # key: f"{project_id}:{user_id}"
        self._limits: dict[str, dict[str, Any]] = {}

    def get_latest_snapshot(self, project_id: str) -> Optional[StateSnapshot]:
        """Retrieves the most recent state snapshot for a project."""
        snapshots = self._snapshots.get(project_id, [])
        if not snapshots:
            return None
        # Assuming last appended is latest
        return snapshots[-1]

    def save_snapshot(self, project_id: str, snapshot: StateSnapshot):
        """Persists a new state snapshot to the in-memory list."""
        if project_id not in self._snapshots:
            self._snapshots[project_id] = []
        self._snapshots[project_id].append(snapshot)

    def save_execution(self, project_id: str, result: ExecutionResult):
        """Persists an execution result to the in-memory list."""
        if project_id not in self._executions:
            self._executions[project_id] = []
        self._executions[project_id].append(result)

    def get_execution_history(
        self, project_id: str, limit: int = 100
    ) -> list[ExecutionResult]:
        """Retrieves the recent execution history."""
        history = self._executions.get(project_id, [])
        return sorted(history, key=lambda x: x.timestamp, reverse=True)[:limit]

    def _get_fact_key(self, project_id: str, user_id: str) -> str:
        return f"{project_id}:{user_id}"

    def get_session_facts(self, project_id: str, user_id: str) -> dict[str, Any]:
        """Retrieves all session facts."""
        return self._facts.get(self._get_fact_key(project_id, user_id), {})

    def save_session_fact(self, project_id: str, user_id: str, key: str, value: Any):
        """Saves or updates a session fact."""
        storage_key = self._get_fact_key(project_id, user_id)
        if storage_key not in self._facts:
            self._facts[storage_key] = {}
        self._facts[storage_key][key] = value

    def delete_session_fact(self, project_id: str, user_id: str, key: str):
        """Deletes a session fact."""
        storage_key = self._get_fact_key(project_id, user_id)
        if storage_key in self._facts:
            self._facts[storage_key].pop(key, None)

    def get_project_limits(self, project_id: str) -> dict[str, Any]:
        """Retrieves project limits."""
        return self._limits.get(project_id, {})

    def set_project_limits(self, project_id: str, limits: dict[str, Any]):
        """Sets project limits."""
        self._limits[project_id] = limits

    def count_recent_executions(self, project_id: str, minutes: int) -> int:
        """Counts successful executions in the last N minutes."""
        history = self._executions.get(project_id, [])
        cutoff = datetime.now(timezone.utc) - timedelta(minutes=minutes)
        # Ensure cutoff is naive if timestamps are naive (which they are by default in pydantic/datetime.now() without tz)
        # Wait, datetime.now() returns naive local time? No, I'm using now(timezone.utc).
        # Check ExecutionResult default: datetime.now(). This is naive local time usually.
        # So I should compare naive to naive.
        cutoff = cutoff.replace(tzinfo=None)
        
        count = 0
        for ex in history:
            if ex.timestamp >= cutoff and ex.status == ExecutionStatus.SUCCESS:
                count += 1
        return count
