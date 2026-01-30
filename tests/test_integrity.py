import pytest
from gradio_chat_agent.execution.engine import ExecutionEngine
from gradio_chat_agent.models.enums import IntentType, ExecutionStatus
from gradio_chat_agent.models.intent import ChatIntent
from gradio_chat_agent.models.state_snapshot import StateSnapshot
from gradio_chat_agent.persistence.in_memory import InMemoryStateRepository
from gradio_chat_agent.registry.in_memory import InMemoryRegistry
from gradio_chat_agent.registry.demo_actions import (
    counter_component,
    set_action,
    set_handler,
)
from gradio_chat_agent.utils import compute_checksum

class TestStateIntegrity:
    @pytest.fixture
    def setup(self):
        registry = InMemoryRegistry()
        repository = InMemoryStateRepository()
        engine = ExecutionEngine(registry, repository)
        project_id = "test-integrity"

        registry.register_component(counter_component)
        registry.register_action(set_action, set_handler)

        return engine, repository, project_id

    def test_checksum_computed_on_save(self, setup):
        engine, repo, pid = setup
        intent = ChatIntent(type=IntentType.ACTION_CALL, request_id="r1", action_id="demo.counter.set", inputs={"value": 42})
        engine.execute_intent(pid, intent, user_roles=["admin"])
        
        latest = repo.get_latest_snapshot(pid)
        assert latest.checksum is not None
        assert latest.checksum == compute_checksum(latest.components)

    def test_integrity_violation_detected(self, setup):
        engine, repo, pid = setup
        # 1. Valid execution
        intent1 = ChatIntent(type=IntentType.ACTION_CALL, request_id="r1", action_id="demo.counter.set", inputs={"value": 10})
        engine.execute_intent(pid, intent1, user_roles=["admin"])
        
        # 2. Tamper
        latest = repo.get_latest_snapshot(pid)
        latest.components["demo.counter"]["value"] = 100 # Tamper
        # Save it back without updating checksum
        repo.save_snapshot(pid, latest)
        
        # 3. Detect
        intent2 = ChatIntent(type=IntentType.ACTION_CALL, request_id="r2", action_id="demo.counter.set", inputs={"value": 20})
        res = engine.execute_intent(pid, intent2, user_roles=["admin"])
        
        assert res.status == ExecutionStatus.FAILED
        assert res.error.code == "integrity_violation"

    def test_revert_computes_checksum(self, setup):
        engine, repo, pid = setup
        # Create a snap
        snap = StateSnapshot(snapshot_id="s1", components={"demo.counter": {"value": 5}}, checksum="wrong")
        repo.save_snapshot(pid, snap)
        
        # Revert
        res = engine.revert_to_snapshot(pid, "s1")
        assert res.status == ExecutionStatus.SUCCESS
        
        latest = repo.get_latest_snapshot(pid)
        assert latest.checksum == compute_checksum(latest.components)
        assert latest.checksum != "wrong"

    def test_checksum_determinism(self):
        c1 = {"a": 1, "b": 2}
        c2 = {"b": 2, "a": 1}
        assert compute_checksum(c1) == compute_checksum(c2)
