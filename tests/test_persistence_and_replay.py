from __future__ import annotations

from datetime import datetime, timezone

from gradio_chat_agent.persistence.db import make_engine, make_session_factory
from gradio_chat_agent.persistence.repo import StateRepository, Identity
from gradio_chat_agent.models.state_snapshot import StateSnapshot
from gradio_chat_agent.models.execution_result import (
    ExecutionResult,
    StateDiffEntry,
)
from gradio_chat_agent.replay.replay import replay_components_from_results


def test_persist_snapshot_and_load_latest(tmp_path):
    db_url = f"sqlite:///{tmp_path}/t.sqlite3"
    engine = make_engine(db_url)
    sf = make_session_factory(engine)
    repo = StateRepository(sf)
    repo.create_tables(engine)

    ident = Identity(session_id="s1", user_id="u1")
    snap = StateSnapshot(
        snapshot_id="snap1",
        timestamp=datetime.now(timezone.utc),
        components={"demo.counter": {"value": 7}},
    )
    repo.save_snapshot(ident, snap)

    loaded = repo.load_latest_snapshot(ident)
    assert loaded is not None
    assert loaded.components["demo.counter"]["value"] == 7


def test_persist_execution_and_replay(tmp_path):
    db_url = f"sqlite:///{tmp_path}/t.sqlite3"
    engine = make_engine(db_url)
    sf = make_session_factory(engine)
    repo = StateRepository(sf)
    repo.create_tables(engine)

    ident = Identity(session_id="s1", user_id="u1")

    r1 = ExecutionResult(
        request_id="r1",
        action_id="demo.counter.increment",
        status="success",
        timestamp=datetime.now(timezone.utc),
        message="ok",
        state_snapshot_id="snapA",
        state_diff=[
            StateDiffEntry(
                path="components.demo.counter.value", op="replace", value=1
            )
        ],
        error=None,
    )
    r2 = ExecutionResult(
        request_id="r2",
        action_id="demo.counter.increment",
        status="success",
        timestamp=datetime.now(timezone.utc),
        message="ok",
        state_snapshot_id="snapB",
        state_diff=[
            StateDiffEntry(
                path="components.demo.counter.value", op="replace", value=3
            )
        ],
        error=None,
    )

    repo.save_execution(ident, r1)
    repo.save_execution(ident, r2)

    execs = repo.list_recent_executions(ident, limit=10)
    rebuilt = replay_components_from_results(
        initial_components={"demo.counter": {"value": 0}}, results=execs
    )
    assert rebuilt["demo.counter"]["value"] == 3
