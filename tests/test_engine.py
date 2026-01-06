from datetime import datetime, timezone

from gradio_chat_agent.execution.engine import (
    EngineStateStore,
    ExecutionEngine,
)
from gradio_chat_agent.execution.modes import ExecutionContext, ModePolicy
from gradio_chat_agent.models.intent import ChatIntent
from gradio_chat_agent.models.state_snapshot import StateSnapshot
from gradio_chat_agent.registry.in_memory import (
    build_action_handlers,
    build_action_registry,
)


def _store():
    return EngineStateStore(
        snapshot=StateSnapshot(
            snapshot_id="s0",
            timestamp=datetime.now(timezone.utc),
            components={"demo.counter": {"value": 0}},
        )
    )


def test_engine_rejects_unknown_action():
    engine = ExecutionEngine(
        action_registry=build_action_registry(),
        handlers=build_action_handlers(),
    )
    store = _store()
    ctx = ExecutionContext(policy=ModePolicy.for_mode("interactive"))

    intent = ChatIntent(
        type="action_call",
        request_id="r1",
        timestamp=datetime.now(timezone.utc),
        execution_mode="interactive",
        action_id="nope.action",
        inputs={},
    )
    result = engine.execute_intent(ctx=ctx, intent=intent, store=store)
    assert result.status == "rejected"
    assert result.error is not None
    assert result.error.code == "action.unknown"


def test_engine_executes_increment():
    engine = ExecutionEngine(
        action_registry=build_action_registry(),
        handlers=build_action_handlers(),
    )
    store = _store()
    ctx = ExecutionContext(policy=ModePolicy.for_mode("interactive"))

    intent = ChatIntent(
        type="action_call",
        request_id="r2",
        timestamp=datetime.now(timezone.utc),
        execution_mode="interactive",
        action_id="demo.counter.increment",
        inputs={"delta": 2},
    )
    result = engine.execute_intent(ctx=ctx, intent=intent, store=store)
    assert result.status == "success"
    assert store.snapshot.components["demo.counter"]["value"] == 2
    assert len(result.state_diff) == 1
    assert result.state_diff[0].path == "components.demo.counter.value"


def test_engine_plan_stops_on_rejection():
    from gradio_chat_agent.execution.plan import ExecutionPlan

    engine = ExecutionEngine(
        action_registry=build_action_registry(),
        handlers=build_action_handlers(),
    )
    store = _store()

    plan = ExecutionPlan(
        plan_id="p1",
        steps=[
            ChatIntent(
                type="action_call",
                request_id="a",
                timestamp=datetime.now(timezone.utc),
                execution_mode="interactive",
                action_id="demo.counter.increment",
                inputs={"delta": 1},
            ),
            ChatIntent(
                type="action_call",
                request_id="b",
                timestamp=datetime.now(timezone.utc),
                execution_mode="interactive",
                action_id="missing.action",
                inputs={},
            ),
            ChatIntent(
                type="action_call",
                request_id="c",
                timestamp=datetime.now(timezone.utc),
                execution_mode="interactive",
                action_id="demo.counter.increment",
                inputs={"delta": 10},
            ),
        ],
    )

    results = engine.execute_plan(plan=plan, mode="interactive", store=store)
    assert len(results) == 2
    assert results[-1].status == "rejected"
    assert store.snapshot.components["demo.counter"]["value"] == 1
