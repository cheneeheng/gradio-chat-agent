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
        self._webhooks: dict[str, dict[str, Any]] = {}
        self._schedules: dict[str, dict[str, Any]] = {}
        self._projects: dict[str, dict[str, Any]] = {}
        self._memberships: dict[str, dict[str, Any]] = {}
        self._users: dict[str, dict[str, Any]] = {}

    def list_projects(self) -> list[dict[str, Any]]:
        """Lists all projects.

        Returns:
            A list of project dictionaries.
        """
        return list(self._projects.values())

    def create_user(self, user_id: str, password_hash: str):
        """Creates a new user.

        Args:
            user_id: The unique identifier for the user.
            password_hash: The hashed password.
        """
        self._users[user_id] = {
            "id": user_id,
            "password_hash": password_hash,
            "created_at": datetime.now(),
        }

    def update_user_password(self, user_id: str, password_hash: str):
        """Updates a user's password.

        Args:
            user_id: The unique identifier for the user.
            password_hash: The new hashed password.
        """
        if user_id in self._users:
            self._users[user_id]["password_hash"] = password_hash

    def list_webhooks(self, project_id: Optional[str] = None) -> list[dict[str, Any]]:
        """Lists all webhooks.

        Args:
            project_id: Optional project ID to filter by.

        Returns:
            A list of webhook dictionaries.
        """
        if project_id:
            return [v for v in self._webhooks.values() if v.get("project_id") == project_id]
        return list(self._webhooks.values())

    def list_enabled_schedules(self) -> list[dict[str, Any]]:
        """Lists all enabled schedules across all projects.

        Returns:
            A list of schedule dictionaries.
        """
        return [v for v in self._schedules.values() if v.get("enabled", True)]

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

    def get_snapshot(self, snapshot_id: str) -> Optional[StateSnapshot]:
        """Retrieves a specific state snapshot by ID.

        Args:
            snapshot_id: The unique ID of the snapshot.

        Returns:
            The StateSnapshot if found, otherwise None.
        """
        # Search all projects (inefficient but fine for in-memory/test)
        for snapshots in self._snapshots.values():
            for snap in snapshots:
                if snap.snapshot_id == snapshot_id:
                    return snap
        return None

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
            result: The execution result object to persist (including intent).
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

    def get_session_facts(
        self, project_id: str, user_id: str
    ) -> dict[str, Any]:
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

    def get_daily_budget_usage(self, project_id: str) -> float:
        """Calculates the total cost of successful executions today.

        Args:
            project_id: The ID of the project.

        Returns:
            The sum of costs for all successful executions since midnight.
        """
        history = self._executions.get(project_id, [])
        now = datetime.now(timezone.utc)
        midnight = now.replace(hour=0, minute=0, second=0, microsecond=0)
        # Ensure cutoff is naive if timestamps are naive
        cutoff = midnight.replace(tzinfo=None)

        total_cost = 0.0
        for ex in history:
            if ex.timestamp >= cutoff and ex.status == ExecutionStatus.SUCCESS:
                total_cost += float(ex.metadata.get("cost", 0.0))
        return total_cost

    def get_webhook(self, webhook_id: str) -> Optional[dict[str, Any]]:
        """Retrieves a webhook configuration by ID.

        Args:
            webhook_id: The unique identifier of the webhook.

        Returns:
            A dictionary containing webhook details.
        """
        return self._webhooks.get(webhook_id)

    def save_webhook(self, webhook: dict[str, Any]):
        """Saves or updates a webhook configuration.

        Args:
            webhook: A dictionary containing webhook details.
        """
        self._webhooks[webhook["id"]] = webhook

    def delete_webhook(self, webhook_id: str):
        """Deletes a webhook configuration.

        Args:
            webhook_id: The unique identifier of the webhook.
        """
        if webhook_id in self._webhooks:
            del self._webhooks[webhook_id]

    def get_schedule(self, schedule_id: str) -> Optional[dict[str, Any]]:
        """Retrieves a schedule configuration by ID.

        Args:
            schedule_id: The unique identifier of the schedule.

        Returns:
            A dictionary containing schedule details.
        """
        return self._schedules.get(schedule_id)

    def save_schedule(self, schedule: dict[str, Any]):
        """Saves or updates a schedule configuration.

        Args:
            schedule: A dictionary containing schedule details.
        """
        self._schedules[schedule["id"]] = schedule

    def delete_schedule(self, schedule_id: str):
        """Deletes a schedule configuration.

        Args:
            schedule_id: The unique identifier of the schedule.
        """
        if schedule_id in self._schedules:
            del self._schedules[schedule_id]

    def create_project(self, project_id: str, name: str):
        """Creates a new project.

        Args:
            project_id: The unique identifier for the project.
            name: Human-readable name of the project.
        """
        self._projects[project_id] = {
            "id": project_id,
            "name": name,
            "created_at": datetime.now(),
            "archived_at": None,
        }

    def is_project_archived(self, project_id: str) -> bool:
        """Checks if a project is archived.

        Args:
            project_id: The ID of the project.

        Returns:
            True if the project is archived, False otherwise.
        """
        project = self._projects.get(project_id)
        if project and project.get("archived_at"):
            return True
        return False

    def archive_project(self, project_id: str):
        """Archives a project.

        Args:
            project_id: The unique identifier for the project.
        """
        if project_id in self._projects:
            self._projects[project_id]["archived_at"] = datetime.now()

    def purge_project(self, project_id: str):
        """Permanently deletes a project and all associated data.

        Args:
            project_id: The unique identifier for the project.
        """
        self._projects.pop(project_id, None)
        self._snapshots.pop(project_id, None)
        self._executions.pop(project_id, None)
        self._limits.pop(project_id, None)
        # Also clean up memberships and facts...
        keys_to_del = [
            k for k in self._memberships if k.startswith(f"{project_id}:")
        ]
        for k in keys_to_del:
            del self._memberships[k]

        fact_keys_to_del = [
            k for k in self._facts if k.startswith(f"{project_id}:")
        ]
        for k in fact_keys_to_del:
            del self._facts[k]

        webhook_keys_to_del = [
            k
            for k, v in self._webhooks.items()
            if v.get("project_id") == project_id
        ]
        for k in webhook_keys_to_del:
            del self._webhooks[k]

        schedule_keys_to_del = [
            k
            for k, v in self._schedules.items()
            if v.get("project_id") == project_id
        ]
        for k in schedule_keys_to_del:
            del self._schedules[k]

    def add_project_member(self, project_id: str, user_id: str, role: str):
        """Adds a member to a project.

        Args:
            project_id: The unique identifier for the project.
            user_id: The unique identifier for the user.
            role: The role to assign (viewer, operator, admin).
        """
        key = f"{project_id}:{user_id}"
        self._memberships[key] = {
            "project_id": project_id,
            "user_id": user_id,
            "role": role,
        }

    def remove_project_member(self, project_id: str, user_id: str):
        """Removes a member from a project.

        Args:
            project_id: The unique identifier for the project.
            user_id: The unique identifier for the user.
        """
        key = f"{project_id}:{user_id}"
        self._memberships.pop(key, None)

    def update_project_member_role(
        self, project_id: str, user_id: str, role: str
    ):
        """Updates a member's role in a project.

        Args:
            project_id: The unique identifier for the project.
            user_id: The unique identifier for the user.
            role: The new role to assign.
        """
        self.add_project_member(project_id, user_id, role)

    def get_project_members(self, project_id: str) -> list[dict[str, str]]:
        """Retrieves all members of a project.

        Args:
            project_id: The unique identifier for the project.

        Returns:
            A list of dictionaries containing user_id and role.
        """
        members = []
        for v in self._memberships.values():
            if v["project_id"] == project_id:
                members.append({"user_id": v["user_id"], "role": v["role"]})
        return members
