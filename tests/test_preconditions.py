from datetime import datetime, timezone

from gradio_chat_agent.execution.preconditions import eval_precondition_expr
from gradio_chat_agent.models.state_snapshot import StateSnapshot


def test_precondition_membership_true():
    snap = StateSnapshot(
        snapshot_id="s",
        timestamp=datetime.now(timezone.utc),
        components={"demo.counter": {"value": 1}},
    )
    assert eval_precondition_expr('"demo.counter" in components', snap) is True


def test_precondition_membership_false():
    snap = StateSnapshot(
        snapshot_id="s",
        timestamp=datetime.now(timezone.utc),
        components={},
    )
    assert (
        eval_precondition_expr('"demo.counter" in components', snap) is False
    )


def test_precondition_get_helper():
    snap = StateSnapshot(
        snapshot_id="s",
        timestamp=datetime.now(timezone.utc),
        components={"demo.counter": {"value": 3}},
    )
    assert (
        eval_precondition_expr(
            'get("components.demo.counter.value", 0) == 3', snap
        )
        is True
    )
