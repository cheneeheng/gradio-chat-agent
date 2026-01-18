"""Persistence layer interfaces and implementations.

This module defines the abstract contract for state persistence.
"""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Optional

from gradio_chat_agent.models.execution_result import (
    ExecutionResult,
    ExecutionStatus,
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
    def save_snapshot(
        self,
        project_id: str,
        snapshot: StateSnapshot,
        is_checkpoint: bool = True,
        parent_id: Optional[str] = None,
    ):
        """Persists a new state snapshot.

        Args:
            project_id: The ID of the project to save the snapshot for.
            snapshot: The snapshot object to persist.
            is_checkpoint: Whether this is a full-state checkpoint.
            parent_id: The ID of the previous snapshot this delta is relative to.
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
    def save_execution_and_snapshot(
        self,
        project_id: str,
        result: ExecutionResult,
        snapshot: StateSnapshot,
        is_checkpoint: bool = True,
        parent_id: Optional[str] = None,
    ):
        """Persists an execution result and a new state snapshot atomically.

        Args:
            project_id: The ID of the project.
            result: The execution result object.
            snapshot: The new state snapshot object.
            is_checkpoint: Whether this is a full-state checkpoint.
            parent_id: The ID of the previous snapshot.
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
    def count_recent_executions(
        self,
        project_id: str,
        minutes: int,
        status: Optional[ExecutionStatus] = None,
    ) -> int:
        """Counts executions in the last N minutes.

        Args:
            project_id: The ID of the project to count executions for.
            minutes: The lookback time window in minutes.
            status: Optional status to filter by.

        Returns:
            The number of executions found in the specified window.
        """

        pass  # pragma: no cover

    @abstractmethod
    def get_daily_budget_usage(self, project_id: str) -> float:
        """Calculates the total cost of successful executions today.

        Args:
            project_id: The ID of the project.

        Returns:
            The sum of costs for all successful executions since midnight.
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

    @abstractmethod
    def save_webhook(self, webhook: dict[str, Any]):
        """Saves or updates a webhook configuration.

        Args:
            webhook: A dictionary containing webhook details.
        """
        pass  # pragma: no cover

    @abstractmethod
    def delete_webhook(self, webhook_id: str):
        """Deletes a webhook configuration.

        Args:
            webhook_id: The unique identifier of the webhook.
        """
        pass  # pragma: no cover

    @abstractmethod
    def rotate_webhook_secret(self, webhook_id: str, new_secret: str):
        """Updates the secret for a webhook.

        Args:
            webhook_id: The unique identifier of the webhook.
            new_secret: The new plain text secret to set.
        """
        pass  # pragma: no cover

    @abstractmethod
    def get_schedule(self, schedule_id: str) -> Optional[dict[str, Any]]:
        """Retrieves a schedule configuration by ID.

        Args:
            schedule_id: The unique identifier of the schedule.

        Returns:
            A dictionary containing schedule details.
        """
        pass  # pragma: no cover

    @abstractmethod
    def save_schedule(self, schedule: dict[str, Any]):
        """Saves or updates a schedule configuration.

        Args:
            schedule: A dictionary containing schedule details.
        """
        pass  # pragma: no cover

    @abstractmethod
    def delete_schedule(self, schedule_id: str):
        """Deletes a schedule configuration.

        Args:
            schedule_id: The unique identifier of the schedule.
        """
        pass  # pragma: no cover

    @abstractmethod
    def create_project(self, project_id: str, name: str):
        """Creates a new project.

        Args:
            project_id: The unique identifier for the project.
            name: Human-readable name of the project.
        """
        pass  # pragma: no cover

    @abstractmethod
    def is_project_archived(self, project_id: str) -> bool:
        """Checks if a project is archived.

        Args:
            project_id: The ID of the project.

        Returns:
            True if the project is archived, False otherwise.
        """
        pass  # pragma: no cover

    @abstractmethod
    def archive_project(self, project_id: str):
        """Archives a project.

        Args:
            project_id: The unique identifier for the project.
        """
        pass  # pragma: no cover

    @abstractmethod
    def purge_project(self, project_id: str):
        """Permanently deletes a project and all associated data.

        Args:
            project_id: The unique identifier for the project.
        """
        pass  # pragma: no cover

    @abstractmethod
    def add_project_member(self, project_id: str, user_id: str, role: str):
        """Adds a member to a project.

        Args:
            project_id: The unique identifier for the project.
            user_id: The unique identifier for the user.
            role: The role to assign (viewer, operator, admin).
        """
        pass  # pragma: no cover

    @abstractmethod
    def remove_project_member(self, project_id: str, user_id: str):
        """Removes a member from a project.

        Args:
            project_id: The unique identifier for the project.
            user_id: The unique identifier for the user.
        """
        pass  # pragma: no cover

    @abstractmethod
    def update_project_member_role(
        self, project_id: str, user_id: str, role: str
    ):
        """Updates a member's role in a project.

        Args:
            project_id: The unique identifier for the project.
            user_id: The unique identifier for the user.
            role: The new role to assign.
        """
        pass  # pragma: no cover

    @abstractmethod
    def list_projects(self) -> list[dict[str, Any]]:
        """Lists all projects.

        Returns:
            A list of project dictionaries.
        """
        pass  # pragma: no cover

    @abstractmethod
    def create_user(
        self,
        user_id: str,
        password_hash: str,
        full_name: Optional[str] = None,
        email: Optional[str] = None,
        organization_id: Optional[str] = None,
    ):
        """Creates a new user.

        Args:
            user_id: The unique identifier for the user.
            password_hash: The hashed password.
            full_name: Optional display name.
            email: Optional contact email.
            organization_id: Optional organization link.
        """
        pass  # pragma: no cover

    @abstractmethod
    def list_users(self) -> list[dict[str, Any]]:
        """Lists all users in the system.

        Returns:
            A list of user dictionaries.
        """
        pass  # pragma: no cover

    @abstractmethod
    def create_api_token(
        self,
        user_id: str,
        name: str,
        token_id: str,
        expires_at: Optional[datetime] = None,
    ):
        """Creates a new API token for a user.

        Args:
            user_id: The ID of the owner.
            name: A label for the token.
            token_id: The unique token identifier.
            expires_at: Optional expiration date.
        """
        pass  # pragma: no cover

    @abstractmethod
    def list_api_tokens(self, user_id: str) -> list[dict[str, Any]]:
        """Lists all tokens for a user.

        Args:
            user_id: The ID of the user.

        Returns:
            A list of token dictionaries.
        """
        pass  # pragma: no cover

    @abstractmethod
    def revoke_api_token(self, token_id: str):
        """Revokes an API token.

        Args:
            token_id: The unique token identifier.
        """
        pass  # pragma: no cover

    @abstractmethod
    def validate_api_token(self, token_id: str) -> Optional[str]:
        """Validates a token and returns the owner user_id if valid.

        Args:
            token_id: The unique token identifier.

        Returns:
            The user_id if valid and not expired/revoked, otherwise None.
        """
        pass  # pragma: no cover

    @abstractmethod
    def delete_user(self, user_id: str):
        """Permanently deletes a user.

        Args:
            user_id: The unique identifier for the user.
        """
        pass  # pragma: no cover

    @abstractmethod
    def get_user(self, user_id: str) -> Optional[dict[str, Any]]:
        """Retrieves a user by ID.

        Args:
            user_id: The unique identifier for the user.

        Returns:
            A dictionary containing user details if found, otherwise None.
        """
        pass  # pragma: no cover

    @abstractmethod
    def update_user_password(self, user_id: str, password_hash: str):
        """Updates a user's password.

        Args:
            user_id: The unique identifier for the user.
            password_hash: The new hashed password.
        """
        pass  # pragma: no cover

    @abstractmethod
    def list_webhooks(
        self, project_id: Optional[str] = None
    ) -> list[dict[str, Any]]:
        """Lists all webhooks.

        Args:
            project_id: Optional project ID to filter by.

        Returns:
            A list of webhook dictionaries.
        """
        pass  # pragma: no cover

    @abstractmethod
    def list_enabled_schedules(self) -> list[dict[str, Any]]:
        """Lists all enabled schedules across all projects.

        Returns:
            A list of schedule dictionaries.
        """
        pass  # pragma: no cover

    @abstractmethod
    def get_project_members(self, project_id: str) -> list[dict[str, str]]:
        """Retrieves all members of a project.

        Args:
            project_id: The unique identifier for the project.

        Returns:
            A list of dictionaries containing user_id and role.
        """
        pass  # pragma: no cover

    @abstractmethod
    def get_org_rollup(self) -> dict[str, Any]:
        """Aggregates usage and execution stats across all projects.

        Returns:
            A dictionary containing platform-wide statistics.
        """
        pass  # pragma: no cover

    @abstractmethod
    def check_health(self) -> bool:
        """Checks the health of the repository (e.g. database connection).

        Returns:
            True if healthy, False otherwise.
        """
        pass  # pragma: no cover

    @abstractmethod
    def acquire_lock(
        self, project_id: str, holder_id: str, timeout_seconds: int = 10
    ) -> bool:
        """Attempts to acquire a distributed lock for a project.

        Args:
            project_id: The ID of the project.
            holder_id: Unique identifier for the lock holder.
            timeout_seconds: How long the lock remains valid.

        Returns:
            True if acquired, False if already held by another holder.
        """
        pass  # pragma: no cover

    @abstractmethod
    def release_lock(self, project_id: str, holder_id: str):
        """Releases a distributed lock.

        Args:
            project_id: The ID of the project.
            holder_id: Unique identifier for the lock holder.
        """
        pass  # pragma: no cover
