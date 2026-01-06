from __future__ import annotations

import hmac
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import pbkdf2_hmac

from sqlalchemy import select

from .models import ProjectMembershipRow, ProjectRow, UserRow


@dataclass(frozen=True)
class AuthIdentity:
    user_id: int
    username: str


def _hash_password(
    password: str, *, salt: bytes, iterations: int = 200_000
) -> bytes:
    return pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)


def hash_password_for_storage(password: str) -> str:
    salt = os.urandom(16)
    digest = _hash_password(password, salt=salt)
    return f"pbkdf2_sha256$200000${salt.hex()}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        algo, iters, salt_hex, digest_hex = stored.split("$", 3)
        if algo != "pbkdf2_sha256":
            return False
        salt = bytes.fromhex(salt_hex)
        expected = bytes.fromhex(digest_hex)
        actual = _hash_password(password, salt=salt, iterations=int(iters))
        return hmac.compare_digest(actual, expected)
    except Exception:
        return False


class AuthRepository:
    def __init__(self, session_factory) -> None:
        self._session_factory = session_factory

    def ensure_default_admin(
        self, *, username: str = "admin", password: str = "admin"
    ) -> None:
        """
        Dev bootstrap only. Change immediately in real deployments.
        Creates:
          - user 'admin'
          - project 'default'
          - membership admin@default => admin
        """
        with self._session_factory() as db:  # Session
            u = db.execute(
                select(UserRow).where(UserRow.username == username)
            ).scalar_one_or_none()
            if u is None:
                u = UserRow(
                    username=username,
                    password_hash=hash_password_for_storage(password),
                    created_at=datetime.now(timezone.utc),
                )
                db.add(u)
                db.flush()

            p = db.execute(
                select(ProjectRow).where(ProjectRow.name == "default")
            ).scalar_one_or_none()
            if p is None:
                p = ProjectRow(
                    name="default", created_at=datetime.now(timezone.utc)
                )
                db.add(p)
                db.flush()

            m = db.execute(
                select(ProjectMembershipRow).where(
                    ProjectMembershipRow.user_id == u.id,
                    ProjectMembershipRow.project_id == p.id,
                )
            ).scalar_one_or_none()
            if m is None:
                db.add(
                    ProjectMembershipRow(
                        user_id=u.id, project_id=p.id, role="admin"
                    )
                )

            db.commit()

    def verify_login(self, username: str, password: str) -> bool:
        with self._session_factory() as db:
            u = db.execute(
                select(UserRow).where(UserRow.username == username)
            ).scalar_one_or_none()
            if u is None:
                return False
            return verify_password(password, u.password_hash)

    def get_user(self, username: str) -> AuthIdentity | None:
        with self._session_factory() as db:
            u = db.execute(
                select(UserRow).where(UserRow.username == username)
            ).scalar_one_or_none()
            if u is None:
                return None
            return AuthIdentity(user_id=u.id, username=u.username)

    def list_projects_for_user(
        self, user_id: int
    ) -> list[tuple[int, str, str]]:
        """
        Returns [(project_id, project_name, role), ...]
        """
        with self._session_factory() as db:
            memberships = db.execute(
                select(
                    ProjectMembershipRow.project_id, ProjectMembershipRow.role
                ).where(ProjectMembershipRow.user_id == user_id)
            ).all()
            if not memberships:
                return []

            project_ids = [m.project_id for m in memberships]
            projects = db.execute(
                select(ProjectRow.id, ProjectRow.name).where(
                    ProjectRow.id.in_(project_ids)
                )
            ).all()
            name_by_id = {pid: name for pid, name in projects}

            out: list[tuple[int, str, str]] = []
            for pid, role in memberships:
                out.append((pid, name_by_id.get(pid, f"project:{pid}"), role))
            out.sort(key=lambda x: x[1])
            return out

    def get_role(self, *, user_id: int, project_id: int) -> str | None:
        with self._session_factory() as db:
            r = db.execute(
                select(ProjectMembershipRow.role).where(
                    ProjectMembershipRow.user_id == user_id,
                    ProjectMembershipRow.project_id == project_id,
                )
            ).scalar_one_or_none()
            return r

    def ensure_project(self, *, name: str) -> int:
        with self._session_factory() as db:
            p = db.execute(
                select(ProjectRow).where(ProjectRow.name == name)
            ).scalar_one_or_none()
            if p is not None:
                return p.id
            p = ProjectRow(name=name, created_at=datetime.now(timezone.utc))
            db.add(p)
            db.flush()
            db.commit()
            return p.id

    def ensure_membership(
        self, *, user_id: int, project_id: int, role: str
    ) -> None:
        with self._session_factory() as db:
            m = db.execute(
                select(ProjectMembershipRow).where(
                    ProjectMembershipRow.user_id == user_id,
                    ProjectMembershipRow.project_id == project_id,
                )
            ).scalar_one_or_none()
            if m is None:
                db.add(
                    ProjectMembershipRow(
                        user_id=user_id, project_id=project_id, role=role
                    )
                )
            else:
                m.role = role
            db.commit()
