from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select

from .models import SessionFactRow
from .repo import ProjectIdentity


class MemoryRepository:
    def __init__(self, session_factory) -> None:
        self._session_factory = session_factory

    def upsert_fact(
        self, *, ident: ProjectIdentity, key: str, value: Any
    ) -> None:
        with self._session_factory() as db:  # Session
            row = db.execute(
                select(SessionFactRow).where(
                    SessionFactRow.user_id == ident.user_id,
                    SessionFactRow.project_id == ident.project_id,
                    SessionFactRow.key == key,
                )
            ).scalar_one_or_none()

            if row is None:
                db.add(
                    SessionFactRow(
                        user_id=ident.user_id,
                        project_id=ident.project_id,
                        key=key,
                        value_json=json.dumps(value, ensure_ascii=False),
                        updated_at=datetime.now(timezone.utc),
                    )
                )
            else:
                row.value_json = json.dumps(value, ensure_ascii=False)
                row.updated_at = datetime.now(timezone.utc)

            db.commit()

    def get_facts(self, *, ident: ProjectIdentity) -> dict[str, Any]:
        with self._session_factory() as db:
            rows = (
                db.execute(
                    select(SessionFactRow).where(
                        SessionFactRow.user_id == ident.user_id,
                        SessionFactRow.project_id == ident.project_id,
                    )
                )
                .scalars()
                .all()
            )

        out: dict[str, Any] = {}
        for r in rows:
            try:
                out[r.key] = json.loads(r.value_json)
            except Exception:
                out[r.key] = r.value_json
        return out
