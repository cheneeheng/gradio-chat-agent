from __future__ import annotations

import json
import threading
from dataclasses import dataclass

from sqlalchemy import delete, desc, select

from ..models.execution_result import (
    ExecutionError,
    ExecutionResult,
    StateDiffEntry,
)
from ..models.state_snapshot import StateSnapshot
from .models import Base, ExecutionRow, SnapshotRow


@dataclass(frozen=True)
class ProjectIdentity:
    user_id: int
    project_id: int


class _KeyedLocks:
    def __init__(self) -> None:
        self._global = threading.Lock()
        self._locks: dict[tuple[int, int], threading.Lock] = {}

    def lock_for(self, key: tuple[int, int]) -> threading.Lock:
        with self._global:
            if key not in self._locks:
                self._locks[key] = threading.Lock()
            return self._locks[key]


class StateRepository:
    def __init__(self, session_factory) -> None:
        self._session_factory = session_factory
        self._locks = _KeyedLocks()

    def create_tables(self, engine) -> None:
        Base.metadata.create_all(engine)

    def load_latest_snapshot(
        self, ident: ProjectIdentity
    ) -> StateSnapshot | None:
        with self._session_factory() as db:  # Session
            row = db.execute(
                select(SnapshotRow)
                .where(
                    SnapshotRow.user_id == ident.user_id,
                    SnapshotRow.project_id == ident.project_id,
                )
                .order_by(desc(SnapshotRow.id))
                .limit(1)
            ).scalar_one_or_none()

            if row is None:
                return None

            return StateSnapshot(
                snapshot_id=row.snapshot_id,
                timestamp=row.created_at,
                components=json.loads(row.components_json),
            )

    def list_recent_executions(
        self, ident: ProjectIdentity, limit: int = 200
    ) -> list[ExecutionResult]:
        with self._session_factory() as db:
            rows = (
                db.execute(
                    select(ExecutionRow)
                    .where(
                        ExecutionRow.user_id == ident.user_id,
                        ExecutionRow.project_id == ident.project_id,
                    )
                    .order_by(desc(ExecutionRow.id))
                    .limit(limit)
                )
                .scalars()
                .all()
            )

            out: list[ExecutionResult] = []
            for r in rows[::-1]:
                err_dict = json.loads(r.error_json) if r.error_json else {}
                diff_list = (
                    json.loads(r.state_diff_json) if r.state_diff_json else []
                )
                out.append(
                    ExecutionResult(
                        request_id=r.request_id,
                        action_id=r.action_id,
                        status=r.status,
                        timestamp=r.created_at,
                        message=r.message,
                        state_snapshot_id=r.snapshot_id,
                        state_diff=[StateDiffEntry(**d) for d in diff_list],
                        error=(
                            ExecutionError(**err_dict) if err_dict else None
                        ),
                    )
                )
            return out

    def save_execution_and_snapshot_atomic(
        self,
        *,
        ident: ProjectIdentity,
        result: ExecutionResult,
        snapshot: StateSnapshot,
    ) -> None:
        lock = self._locks.lock_for((ident.user_id, ident.project_id))
        with lock:
            with self._session_factory() as db:
                err = result.error.model_dump() if result.error else {}
                diff = [d.model_dump() for d in result.state_diff]

                db.add(
                    ExecutionRow(
                        user_id=ident.user_id,
                        project_id=ident.project_id,
                        request_id=result.request_id,
                        action_id=result.action_id,
                        status=result.status,
                        created_at=result.timestamp,
                        message=result.message,
                        error_json=json.dumps(err, ensure_ascii=False),
                        state_diff_json=json.dumps(diff, ensure_ascii=False),
                        snapshot_id=result.state_snapshot_id,
                    )
                )

                db.add(
                    SnapshotRow(
                        user_id=ident.user_id,
                        project_id=ident.project_id,
                        snapshot_id=snapshot.snapshot_id,
                        created_at=snapshot.timestamp,
                        components_json=json.dumps(
                            snapshot.components, ensure_ascii=False
                        ),
                    )
                )

                db.commit()

    def clear_project(self, ident: ProjectIdentity) -> None:
        lock = self._locks.lock_for((ident.user_id, ident.project_id))
        with lock:
            with self._session_factory() as db:
                db.execute(
                    delete(ExecutionRow).where(
                        ExecutionRow.user_id == ident.user_id,
                        ExecutionRow.project_id == ident.project_id,
                    )
                )
                db.execute(
                    delete(SnapshotRow).where(
                        SnapshotRow.user_id == ident.user_id,
                        SnapshotRow.project_id == ident.project_id,
                    )
                )
                db.commit()
