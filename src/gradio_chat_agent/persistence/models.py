"""SQLAlchemy models for the persistence layer."""

from datetime import datetime
from typing import Any, Optional

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow
    )
    archived_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime, nullable=True
    )

    snapshots: Mapped[list["Snapshot"]] = relationship(back_populates="project")
    executions: Mapped[list["Execution"]] = relationship(
        back_populates="project"
    )
    facts: Mapped[list["SessionFact"]] = relationship(back_populates="project")
    limits: Mapped[Optional["ProjectLimits"]] = relationship(
        back_populates="project", uselist=False
    )


class ProjectLimits(Base):
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
    __tablename__ = "snapshots"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"))
    timestamp: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow
    )
    components: Mapped[dict[str, Any]] = mapped_column(JSON)

    project: Mapped["Project"] = relationship(back_populates="snapshots")


class Execution(Base):
    __tablename__ = "executions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
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
    error: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, nullable=True)

    project: Mapped["Project"] = relationship(back_populates="executions")


class SessionFact(Base):
    __tablename__ = "session_facts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"))
    user_id: Mapped[str] = mapped_column(String)
    key: Mapped[str] = mapped_column(String)
    value: Mapped[Any] = mapped_column(JSON)

    project: Mapped["Project"] = relationship(back_populates="facts")

    __table_args__ = (
        UniqueConstraint("project_id", "user_id", "key", name="uq_project_user_key"),
    )
