"""SQLAlchemy models for the persistence layer.

This module defines the database schema for projects, snapshots, executions,
session facts, and project limits using SQLAlchemy ORM.
"""

from datetime import datetime
from typing import Any, Optional

from sqlalchemy import (
    JSON,
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models."""

    pass


class Project(Base):
    """Represents a project in the system.

    A project is a logical container for application state, history, and
    governance policies.

    Attributes:
        id: Unique identifier for the project.
        name: Human-readable name of the project.
        created_at: Timestamp when the project was created.
        archived_at: Timestamp when the project was archived, if applicable.
        snapshots: List of state snapshots associated with the project.
        executions: List of execution results associated with the project.
        facts: List of session facts associated with the project.
        limits: Governance limits and policies for the project.
    """

    __tablename__ = "projects"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow
    )
    archived_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime, nullable=True
    )

    snapshots: Mapped[list["Snapshot"]] = relationship(
        back_populates="project"
    )
    executions: Mapped[list["Execution"]] = relationship(
        back_populates="project"
    )
    facts: Mapped[list["SessionFact"]] = relationship(back_populates="project")
    limits: Mapped[Optional["ProjectLimits"]] = relationship(
        back_populates="project", uselist=False
    )


class ProjectLimits(Base):
    """Represents governance limits and policies for a project.

    Attributes:
        project_id: The ID of the project these limits apply to.
        rate_limit_minute: Maximum allowed executions per minute.
        rate_limit_hour: Maximum allowed executions per hour.
        daily_budget: Maximum daily budget for executions.
        raw_policy: The complete policy configuration stored as a JSON blob.
        project: The project associated with these limits.
    """

    __tablename__ = "project_limits"

    project_id: Mapped[str] = mapped_column(
        ForeignKey("projects.id"), primary_key=True
    )
    rate_limit_minute: Mapped[int] = mapped_column(Integer, default=60)
    rate_limit_hour: Mapped[int] = mapped_column(Integer, default=1000)
    daily_budget: Mapped[int] = mapped_column(Integer, default=1000)
    raw_policy: Mapped[Optional[dict[str, Any]]] = mapped_column(
        JSON, nullable=True
    )

    project: Mapped["Project"] = relationship(back_populates="limits")


class Snapshot(Base):
    """Represents an immutable snapshot of a project's state.

    Attributes:
        id: Unique identifier for the snapshot.
        project_id: The ID of the project this snapshot belongs to.
        timestamp: Timestamp when the snapshot was captured.
        components: JSON blob representing the state of all components.
        project: The project associated with this snapshot.
    """

    __tablename__ = "snapshots"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"))
    timestamp: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow
    )
    components: Mapped[dict[str, Any]] = mapped_column(JSON)

    project: Mapped["Project"] = relationship(back_populates="snapshots")


class Execution(Base):
    """Represents an audit log entry for an attempted action.

    Attributes:
        id: Internal database identifier.
        request_id: Unique identifier for the originating intent.
        project_id: The ID of the project context.
        action_id: The ID of the action that was attempted.
        status: The outcome status (e.g., 'success', 'rejected', 'failed').
        timestamp: Timestamp when the execution completed.
        message: Human-readable summary of the outcome.
        state_snapshot_id: The ID of the resulting state snapshot.
        state_diff: JSON blob describing the state delta applied.
        error: JSON blob containing error details if the execution failed.
        project: The project associated with this execution.
    """

    __tablename__ = "executions"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    request_id: Mapped[str] = mapped_column(String, unique=True)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"))
    action_id: Mapped[str] = mapped_column(String)
    status: Mapped[str] = mapped_column(String)  # success, rejected, failed
    timestamp: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow
    )
    message: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    state_snapshot_id: Mapped[str] = mapped_column(ForeignKey("snapshots.id"))
    state_diff: Mapped[list[dict[str, Any]]] = mapped_column(JSON)
    error: Mapped[Optional[dict[str, Any]]] = mapped_column(
        JSON, nullable=True
    )

    project: Mapped["Project"] = relationship(back_populates="executions")


class SessionFact(Base):
    """Represents a session-specific fact stored for an agent.

    Attributes:
        id: Internal database identifier.
        project_id: The ID of the project context.
        user_id: The ID of the user the fact belongs to.
        key: Unique key for the fact within the session.
        value: The value stored for the fact.
        project: The project associated with this fact.
    """

    __tablename__ = "session_facts"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"))
    user_id: Mapped[str] = mapped_column(String)
    key: Mapped[str] = mapped_column(String)
    value: Mapped[Any] = mapped_column(JSON)

    project: Mapped["Project"] = relationship(back_populates="facts")

    __table_args__ = (
        UniqueConstraint(
            "project_id", "user_id", "key", name="uq_project_user_key"
        ),
    )
