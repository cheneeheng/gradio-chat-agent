"""In-memory implementation of the StateRepository.

This module provides a thread-safe, ephemeral state repository suitable for
testing and local development.
"""

from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from gradio_chat_agent.models.execution_result import (
    ExecutionResult,
    ExecutionStatus,
)
from gradio_chat_agent.models.state_snapshot import StateSnapshot
from gradio_chat_agent.persistence.repository import StateRepository


class InMemoryStateRepository(StateRepository):
    """In-memory implementation of the StateRepository.

    Useful for unit tests and local development where persistence across
    restarts is not required.
    """

    def __init__(self):
        """Initializes the empty in-memory stores."""
        self._snapshots: dict[str, list[StateSnapshot]] = {}
        self._executions: dict[str, list[ExecutionResult]] = {}
        self._facts: dict[
            str, dict[str, Any]
        ] = {}  # key: f"{project_id}:{user_id}"
        self._limits: dict[str, dict[str, Any]] = {}

    def get_latest_snapshot(self, project_id: str) -> Optional[StateSnapshot]:
        """Retrieves the most recent state snapshot for a project.

        Args:
            project_id: The ID of the project to retrieve the snapshot for.

        Returns:
            The latest StateSnapshot, or None if the project has no history.
        """
        snapshots = self._snapshots.get(project_id, [])
        if not snapshots:
            return None
        # Assuming last appended is latest
        return snapshots[-1]

    def save_snapshot(self, project_id: str, snapshot: StateSnapshot):
        """Persists a new state snapshot to the in-memory list.

        Args:
            project_id: The ID of the project to save the snapshot for.
            snapshot: The snapshot object to persist.
        """
        if project_id not in self._snapshots:
            self._snapshots[project_id] = []
        self._snapshots[project_id].append(snapshot)

    def save_execution(self, project_id: str, result: ExecutionResult):
        """Persists an execution result to the in-memory list.

        Args:
            project_id: The ID of the project the execution belongs to.
            result: The execution result object to persist.
        """
        if project_id not in self._executions:
            self._executions[project_id] = []
        self._executions[project_id].append(result)

    def get_execution_history(
        self, project_id: str, limit: int = 100
    ) -> list[ExecutionResult]:
        """Retrieves the recent execution history.

        Args:
            project_id: The ID of the project to retrieve history for.
            limit: Maximum number of records to return. Defaults to 100.

        Returns:
            A list of ExecutionResult objects, ordered by timestamp descending.
        """
        history = self._executions.get(project_id, [])
        return sorted(history, key=lambda x: x.timestamp, reverse=True)[:limit]

    def _get_fact_key(self, project_id: str, user_id: str) -> str:
        """Generates a storage key for session facts.

        Args:
            project_id: The ID of the project.
            user_id: The ID of the user.

        Returns:
            A string key in the format '{project_id}:{user_id}'.
        """
        return f"{project_id}:{user_id}"

    def get_session_facts(self, project_id: str, user_id: str) -> dict[str, Any]:
        """Retrieves all session facts.

        Args:
            project_id: The ID of the project.
            user_id: The ID of the user.

        Returns:
            A dictionary of key-value facts stored for this user and project.
        """
        return self._facts.get(self._get_fact_key(project_id, user_id), {})

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
        storage_key = self._get_fact_key(project_id, user_id)
        if storage_key not in self._facts:
            self._facts[storage_key] = {}
        self._facts[storage_key][key] = value

    def delete_session_fact(self, project_id: str, user_id: str, key: str):
        """Deletes a session fact.

        Args:
            project_id: The ID of the project.
            user_id: The ID of the user.
            key: The key of the fact to remove.
        """
        storage_key = self._get_fact_key(project_id, user_id)
        if storage_key in self._facts:
            self._facts[storage_key].pop(key, None)

    def get_project_limits(self, project_id: str) -> dict[str, Any]:
        """Retrieves project limits.

        Args:
            project_id: The ID of the project to retrieve limits for.

        Returns:
            A dictionary containing limit configuration and governance policies.
        """
        return self._limits.get(project_id, {})

    def set_project_limits(self, project_id: str, policy: dict[str, Any]):
        """Sets project limits.

        Args:
            project_id: The ID of the project to update limits for.
            policy: The policy dictionary containing limits configuration.
        """
        self._limits[project_id] = policy

    def count_recent_executions(self, project_id: str, minutes: int) -> int:
        """Counts successful executions in the last N minutes.

        Args:
            project_id: The ID of the project to count executions for.
            minutes: The lookback time window in minutes.

        Returns:
            The number of successful executions found in the specified window.
        """
        history = self._executions.get(project_id, [])
        cutoff = datetime.now(timezone.utc) - timedelta(minutes=minutes)
        # Ensure cutoff is naive if timestamps are naive
        cutoff = cutoff.replace(tzinfo=None)

        count = 0
        for ex in history:
            if ex.timestamp >= cutoff and ex.status == ExecutionStatus.SUCCESS:
                count += 1
        return count
