import json
from datetime import datetime, timezone

from gradio_chat_agent.observability.export import export_session_json
from gradio_chat_agent.persistence.db import make_engine, make_session_factory
from gradio_chat_agent.persistence.repo import StateRepository, Identity
from gradio_chat_agent.persistence.memory_repo import MemoryRepository
from gradio_chat_agent.models.state_snapshot import StateSnapshot
from gradio_chat_agent.models.execution_result import ExecutionResult


def test_export_payload(tmp_path):
    db_url = f"sqlite:///{tmp_path}/t.sqlite3"
    engine = make_engine(db_url)
    sf = make_session_factory(engine)

    repo = StateRepository(sf)
    repo.create_tables(engine)
    mem = MemoryRepository(sf)

    ident = Identity(session_id="s1", user_id="u1")

    snap = StateSnapshot(
        snapshot_id="snap1",
        timestamp=datetime.now(timezone.utc),
        components={"demo.counter": {"value": 5}},
    )
    repo.save_execution_and_snapshot_atomic(
        ident=ident,
        result=ExecutionResult(
            request_id="r",
            action_id="system.noop",
            status="success",
            timestamp=datetime.now(timezone.utc),
            message="ok",
            state_snapshot_id="snap1",
            state_diff=[],
            error=None,
        ),
        snapshot=snap,
    )
    mem.upsert_fact(ident=ident, key="selected_model", value="demo")

    payload = json.loads(export_session_json(repo, mem, ident))
    assert (
        payload["latest_snapshot"]["components"]["demo.counter"]["value"] == 5
    )
    assert payload["facts"]["selected_model"] == "demo"
    assert len(payload["executions"]) >= 1
