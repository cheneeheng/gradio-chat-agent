from datetime import datetime, timezone

from gradio_chat_agent.persistence.db import make_engine, make_session_factory
from gradio_chat_agent.persistence.repo import StateRepository, ProjectIdentity
from gradio_chat_agent.persistence.auth_repo import AuthRepository
from gradio_chat_agent.models.state_snapshot import StateSnapshot
from gradio_chat_agent.models.execution_result import ExecutionResult


def test_project_scoped_snapshots_are_isolated(tmp_path):
    db_url = f"sqlite:///{tmp_path}/t.sqlite3"
    engine = make_engine(db_url)
    sf = make_session_factory(engine)

    repo = StateRepository(sf)
    repo.create_tables(engine)

    auth = AuthRepository(sf)
    auth.ensure_default_admin(username="admin", password="admin")
    admin = auth.get_user("admin")
    assert admin is not None

    p1 = auth.ensure_project(name="p1")
    p2 = auth.ensure_project(name="p2")
    auth.ensure_membership(user_id=admin.user_id, project_id=p1, role="admin")
    auth.ensure_membership(user_id=admin.user_id, project_id=p2, role="admin")

    ident1 = ProjectIdentity(user_id=admin.user_id, project_id=p1)
    ident2 = ProjectIdentity(user_id=admin.user_id, project_id=p2)

    s1 = StateSnapshot(
        snapshot_id="s1",
        timestamp=datetime.now(timezone.utc),
        components={"demo.counter": {"value": 1}},
    )
    s2 = StateSnapshot(
        snapshot_id="s2",
        timestamp=datetime.now(timezone.utc),
        components={"demo.counter": {"value": 99}},
    )

    repo.save_execution_and_snapshot_atomic(
        ident=ident1,
        result=ExecutionResult(
            request_id="r1",
            action_id="system.noop",
            status="success",
            timestamp=datetime.now(timezone.utc),
            message="ok",
            state_snapshot_id="s1",
            state_diff=[],
            error=None,
        ),
        snapshot=s1,
    )
    repo.save_execution_and_snapshot_atomic(
        ident=ident2,
        result=ExecutionResult(
            request_id="r2",
            action_id="system.noop",
            status="success",
            timestamp=datetime.now(timezone.utc),
            message="ok",
            state_snapshot_id="s2",
            state_diff=[],
            error=None,
        ),
        snapshot=s2,
    )

    l1 = repo.load_latest_snapshot(ident1)
    l2 = repo.load_latest_snapshot(ident2)
    assert l1 is not None and l2 is not None
    assert l1.components["demo.counter"]["value"] == 1
    assert l2.components["demo.counter"]["value"] == 99
