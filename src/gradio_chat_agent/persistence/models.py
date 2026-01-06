from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class UserRow(Base):
    __tablename__ = "users"
    __table_args__ = (UniqueConstraint("username", name="uq_users_username"),)

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    username: Mapped[str] = mapped_column(String(128), index=True)
    password_hash: Mapped[str] = mapped_column(String(256))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), index=True
    )


class ProjectRow(Base):
    __tablename__ = "projects"
    __table_args__ = (UniqueConstraint("name", name="uq_projects_name"),)

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    name: Mapped[str] = mapped_column(String(128), index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), index=True
    )

    archived_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), index=True
    )


class ProjectMembershipRow(Base):
    __tablename__ = "project_memberships"
    __table_args__ = (
        UniqueConstraint(
            "user_id", "project_id", name="uq_project_membership"
        ),
    )

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    user_id: Mapped[int] = mapped_column(Integer, index=True)
    project_id: Mapped[int] = mapped_column(Integer, index=True)

    # one of: viewer | operator | admin
    role: Mapped[str] = mapped_column(String(32), index=True)


class SnapshotRow(Base):
    __tablename__ = "snapshots"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    user_id: Mapped[int] = mapped_column(Integer, index=True)
    project_id: Mapped[int] = mapped_column(Integer, index=True)

    snapshot_id: Mapped[str] = mapped_column(String(256), index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), index=True
    )

    # JSON string of StateSnapshot.components
    components_json: Mapped[str] = mapped_column(Text)


class ExecutionRow(Base):
    __tablename__ = "executions"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    user_id: Mapped[int] = mapped_column(Integer, index=True)
    project_id: Mapped[int] = mapped_column(Integer, index=True)

    request_id: Mapped[str] = mapped_column(String(256), index=True)
    action_id: Mapped[str] = mapped_column(String(256), index=True)
    status: Mapped[str] = mapped_column(String(32), index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), index=True
    )

    message: Mapped[str] = mapped_column(Text)
    error_json: Mapped[str] = mapped_column(Text)  # JSON string or "{}"
    state_diff_json: Mapped[str] = mapped_column(Text)  # JSON string "[]"
    snapshot_id: Mapped[str] = mapped_column(String(256), index=True)


class SessionFactRow(Base):
    __tablename__ = "session_facts"
    __table_args__ = (
        UniqueConstraint(
            "user_id", "project_id", "key", name="uq_project_fact_key"
        ),
    )

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    user_id: Mapped[int] = mapped_column(Integer, index=True)
    project_id: Mapped[int] = mapped_column(Integer, index=True)

    key: Mapped[str] = mapped_column(String(128), index=True)
    value_json: Mapped[str] = mapped_column(Text)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), index=True
    )


class WebhookRow(Base):
    __tablename__ = "webhooks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project_id: Mapped[int] = mapped_column(Integer, index=True)
    secret: Mapped[str] = mapped_column(String(256))
    action_id: Mapped[str] = mapped_column(String(256))
    inputs_template: Mapped[str] = mapped_column(Text)


class ScheduleRow(Base):
    __tablename__ = "schedules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project_id: Mapped[int]
    action_id: Mapped[str]
    inputs_json: Mapped[str]
    cron: Mapped[str]
    enabled: Mapped[bool]


class ProjectLimitsRow(Base):
    __tablename__ = "project_limits"

    project_id: Mapped[int] = mapped_column(Integer, primary_key=True)

    # rate limiting
    max_actions_per_minute: Mapped[int | None]
    max_actions_per_hour: Mapped[int | None]

    # quota
    max_actions_per_day: Mapped[int | None]

    # budget (abstract units)
    daily_budget: Mapped[int | None]
    budget_used_today: Mapped[int] = mapped_column(Integer, default=0)
    budget_reset_at: Mapped[datetime | None]


class ActionBudgetRow(Base):
    __tablename__ = "action_budgets"

    project_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    action_id: Mapped[str] = mapped_column(String(256), primary_key=True)

    daily_budget: Mapped[int | None]
    budget_used_today: Mapped[int] = mapped_column(Integer, default=0)
    budget_reset_at: Mapped[datetime | None]


class AlertRuleRow(Base):
    __tablename__ = "alert_rules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project_id: Mapped[int]
    threshold_percent: Mapped[int]  # e.g. 80, 90
    webhook_url: Mapped[str]
    enabled: Mapped[bool]


class ApprovalRuleRow(Base):
    __tablename__ = "approval_rules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project_id: Mapped[int]
    min_cost: Mapped[int]  # e.g. require approval if cost ≥ 20
    required_role: Mapped[str]  # e.g. admin
    enabled: Mapped[bool]
