from datetime import datetime, timezone

from gradio_chat_agent.execution.engine import (
    ExecutionEngine,
    EngineStateStore,
)
from gradio_chat_agent.execution.modes import ExecutionContext, ModePolicy
from gradio_chat_agent.models.intent import ChatIntent
from gradio_chat_agent.models.state_snapshot import StateSnapshot
from gradio_chat_agent.registry.in_memory import (
    build_action_handlers,
    build_action_registry,
)


def test_engine_denies_missing_role():
    actions = build_action_registry()
    handlers = build_action_handlers()
    engine = ExecutionEngine(action_registry=actions, handlers=handlers)

    store = EngineStateStore(
        snapshot=StateSnapshot(
            snapshot_id="s0",
            timestamp=datetime.now(timezone.utc),
            components={"demo.counter": {"value": 0}},
        )
    )

    ctx = ExecutionContext(
        policy=ModePolicy.for_mode("interactive"),
        user_id="u",
        user_roles=["user"],
    )

    intent = ChatIntent(
        type="action_call",
        request_id="r",
        timestamp=datetime.now(timezone.utc),
        execution_mode="interactive",
        action_id="demo.counter.increment",  # admin-only in the example registry
        inputs={"delta": 1},
    )

    result = engine.execute_intent(ctx=ctx, intent=intent, store=store)
    assert result.status == "rejected"
    assert result.error is not None
    assert result.error.code == "permission.denied"
