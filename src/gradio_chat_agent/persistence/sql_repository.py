"""SQLAlchemy implementation of the StateRepository."""

from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from sqlalchemy import create_engine, delete, func, select
from sqlalchemy.orm import sessionmaker

from gradio_chat_agent.models.execution_result import (
    ExecutionError,
    ExecutionResult,
    StateDiffEntry,
)
from gradio_chat_agent.models.state_snapshot import StateSnapshot
from gradio_chat_agent.persistence.models import (
    Base,
    Execution,
    Project,
    ProjectLimits,
    SessionFact,
    Snapshot,
)
from gradio_chat_agent.persistence.repository import StateRepository


class SQLStateRepository(StateRepository):
    """Production-ready SQL persistence layer."""

    def __init__(self, database_url: str):
        """Initialize the repository with a database URL.

        Args:
            database_url: SQLAlchemy connection string.
        """
        self.engine = create_engine(database_url)
        # In a real prod env, use Alembic. For now, auto-create.
        Base.metadata.create_all(self.engine)
        self.SessionLocal = sessionmaker(bind=self.engine)

        # Ensure default project exists
        self._ensure_project("default_project")

    def _ensure_project(self, project_id: str):
        """Ensures a project exists in the database.

        Args:
            project_id: The unique identifier for the project.
        """
        with self.SessionLocal() as session:
            project = session.get(Project, project_id)
            if not project:
                session.add(Project(id=project_id, name="Default Project"))
                session.commit()

    def get_latest_snapshot(self, project_id: str) -> Optional[StateSnapshot]:
        """Retrieves the most recent state snapshot for a project.

        Args:
            project_id: The ID of the project to retrieve the snapshot for.

        Returns:
            The latest StateSnapshot, or None if the project has no history.
        """
        with self.SessionLocal() as session:
            stmt = (
                select(Snapshot)
                .where(Snapshot.project_id == project_id)
                .order_by(Snapshot.timestamp.desc())
                .limit(1)
            )
            row = session.execute(stmt).scalar_one_or_none()
            if not row:
                return None

            return StateSnapshot(
                snapshot_id=row.id,
                timestamp=row.timestamp,
                components=row.components,
            )

    def save_snapshot(self, project_id: str, snapshot: StateSnapshot):
        """Persists a new state snapshot.

        Args:
            project_id: The ID of the project to save the snapshot for.
            snapshot: The snapshot object to persist.
        """
        with self.SessionLocal() as session:
            self._ensure_project(project_id)

            db_snapshot = Snapshot(
                id=snapshot.snapshot_id,
                project_id=project_id,
                timestamp=snapshot.timestamp,
                components=snapshot.components,
            )
            session.add(db_snapshot)
            session.commit()

    def save_execution(self, project_id: str, result: ExecutionResult):
        """Persists an execution result (audit log entry).

        Args:
            project_id: The ID of the project the execution belongs to.
            result: The execution result object to persist.
        """
        with self.SessionLocal() as session:
            self._ensure_project(project_id)

            # Serialize state_diff and error
            state_diff_json = [
                d.model_dump(mode="json") for d in result.state_diff
            ]
            error_json = (
                result.error.model_dump(mode="json") if result.error else None
            )

            db_exec = Execution(
                request_id=result.request_id,
                project_id=project_id,
                action_id=result.action_id,
                status=result.status,
                timestamp=result.timestamp,
                message=result.message,
                state_snapshot_id=result.state_snapshot_id,
                state_diff=state_diff_json,
                error=error_json,
            )
            session.add(db_exec)
            session.commit()

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
        with self.SessionLocal() as session:
            stmt = (
                select(Execution)
                .where(Execution.project_id == project_id)
                .order_by(Execution.timestamp.desc())
                .limit(limit)
            )
            rows = session.execute(stmt).scalars().all()

            results = []
            for row in rows:
                diffs = [StateDiffEntry(**d) for d in row.state_diff]
                error = ExecutionError(**row.error) if row.error else None

                results.append(
                    ExecutionResult(
                        request_id=row.request_id,
                        action_id=row.action_id,
                        status=row.status,
                        timestamp=row.timestamp,
                        message=row.message,
                        state_snapshot_id=row.state_snapshot_id,
                        state_diff=diffs,
                        error=error,
                    )
                )
            return results

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
        with self.SessionLocal() as session:
            stmt = select(SessionFact).where(
                SessionFact.project_id == project_id,
                SessionFact.user_id == user_id,
            )
            rows = session.execute(stmt).scalars().all()
            return {row.key: row.value for row in rows}

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
        with self.SessionLocal() as session:
            self._ensure_project(project_id)

            stmt = select(SessionFact).where(
                SessionFact.project_id == project_id,
                SessionFact.user_id == user_id,
                SessionFact.key == key,
            )
            existing = session.execute(stmt).scalar_one_or_none()

            if existing:
                existing.value = value
            else:
                session.add(
                    SessionFact(
                        project_id=project_id,
                        user_id=user_id,
                        key=key,
                        value=value,
                    )
                )
            session.commit()

    def delete_session_fact(self, project_id: str, user_id: str, key: str):
        """Deletes a session fact.

        Args:
            project_id: The ID of the project.
            user_id: The ID of the user.
            key: The key of the fact to remove.
        """
        with self.SessionLocal() as session:
            stmt = delete(SessionFact).where(
                SessionFact.project_id == project_id,
                SessionFact.user_id == user_id,
                SessionFact.key == key,
            )
            session.execute(stmt)
            session.commit()

    def get_project_limits(self, project_id: str) -> dict[str, Any]:
        """Retrieves project limits and policy.

        Args:
            project_id: The ID of the project to retrieve limits for.

        Returns:
            A dictionary containing limit configuration and governance policies.
        """
        with self.SessionLocal() as session:
            project_limits = session.get(ProjectLimits, project_id)
            if project_limits and project_limits.raw_policy:
                return project_limits.raw_policy
            return {}

    def set_project_limits(self, project_id: str, policy: dict[str, Any]):
        """Sets project limits.

        Args:
            project_id: The ID of the project to update limits for.
            policy: The policy dictionary containing limits configuration.
        """
        with self.SessionLocal() as session:
            self._ensure_project(project_id)
            project_limits = session.get(ProjectLimits, project_id)
            if not project_limits:
                project_limits = ProjectLimits(project_id=project_id)
                session.add(project_limits)

            project_limits.raw_policy = policy
            # Sync specific columns
            if "limits" in policy and "rate" in policy["limits"]:
                rate = policy["limits"]["rate"]
                if "per_minute" in rate:
                    project_limits.rate_limit_minute = rate["per_minute"]
                if "per_hour" in rate:
                    project_limits.rate_limit_hour = rate["per_hour"]

            if "limits" in policy and "budget" in policy["limits"]:
                if "daily" in policy["limits"]["budget"]:
                    project_limits.daily_budget = policy["limits"]["budget"][
                        "daily"
                    ]

            session.commit()

    def count_recent_executions(self, project_id: str, minutes: int) -> int:
        """Counts successful executions in the last N minutes.

        Args:
            project_id: The ID of the project to count executions for.
            minutes: The lookback time window in minutes.

        Returns:
            The number of successful executions found in the specified window.
        """
        cutoff = datetime.now(timezone.utc) - timedelta(minutes=minutes)
        with self.SessionLocal() as session:
            stmt = (
                select(func.count())
                .select_from(Execution)
                .where(
                    Execution.project_id == project_id,
                    Execution.timestamp >= cutoff.replace(tzinfo=None),
                    Execution.status == "success",
                )
            )
            return session.execute(stmt).scalar()
