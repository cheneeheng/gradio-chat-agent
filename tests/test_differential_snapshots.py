import pytest
from gradio_chat_agent.execution.engine import ExecutionEngine
from gradio_chat_agent.persistence.sql_repository import SQLStateRepository
from gradio_chat_agent.persistence.in_memory import InMemoryStateRepository
from gradio_chat_agent.registry.in_memory import InMemoryRegistry
from gradio_chat_agent.registry.demo_actions import (
    counter_component, set_action, set_handler
)
from gradio_chat_agent.models.intent import ChatIntent
from gradio_chat_agent.models.enums import IntentType, ExecutionStatus
from gradio_chat_agent.models.state_snapshot import StateSnapshot

class TestDifferentialSnapshots:
    @pytest.fixture
    def setup_sql(self):
        repo = SQLStateRepository("sqlite:///:memory:")
        registry = InMemoryRegistry()
        engine = ExecutionEngine(registry, repo)
        pid = "test-p"
        registry.register_component(counter_component)
        registry.register_action(set_action, set_handler)
        return engine, repo, pid

    @pytest.fixture
    def setup_in_memory(self):
        repo = InMemoryStateRepository()
        registry = InMemoryRegistry()
        engine = ExecutionEngine(registry, repo)
        pid = "test-p"
        registry.register_component(counter_component)
        registry.register_action(set_action, set_handler)
        return engine, repo, pid

    def test_sql_differential_storage(self, setup_sql):
        engine, repo, pid = setup_sql
        
        # 1st success: Checkpoint
        engine.execute_intent(pid, ChatIntent(type=IntentType.ACTION_CALL, request_id="r1", action_id="demo.counter.set", inputs={"value": 10}), user_roles=["admin"])
        
        # 2nd success: Delta
        engine.execute_intent(pid, ChatIntent(type=IntentType.ACTION_CALL, request_id="r2", action_id="demo.counter.set", inputs={"value": 20}), user_roles=["admin"])
        
        from gradio_chat_agent.persistence.models import Snapshot
        with repo.SessionLocal() as session:
            from sqlalchemy import select
            snapshots = session.execute(select(Snapshot).order_by(Snapshot.timestamp)).scalars().all()
            assert len(snapshots) == 2
            assert snapshots[0].is_checkpoint is True
            assert snapshots[1].is_checkpoint is False
            assert snapshots[1].parent_id == snapshots[0].id
            assert "_delta" in snapshots[1].components
            assert "diffs" in snapshots[1].components["_delta"]

    def test_sql_state_reconstruction(self, setup_sql):
        engine, repo, pid = setup_sql
        
        for i in range(1, 4):
            engine.execute_intent(pid, ChatIntent(type=IntentType.ACTION_CALL, request_id=f"r{i}", action_id="demo.counter.set", inputs={"value": i*10}), user_roles=["admin"])
            
        latest = repo.get_latest_snapshot(pid)
        assert latest.components["demo.counter"]["value"] == 30
        assert latest.is_checkpoint is False # Only 1st was checkpoint

    def test_in_memory_reconstruction(self, setup_in_memory):
        engine, repo, pid = setup_in_memory
        
        for i in range(1, 3):
            engine.execute_intent(pid, ChatIntent(type=IntentType.ACTION_CALL, request_id=f"r{i}", action_id="demo.counter.set", inputs={"value": i*5}), user_roles=["admin"])
            
        latest = repo.get_latest_snapshot(pid)
        assert latest.components["demo.counter"]["value"] == 10

    def test_sql_reconstruct_snapshot_parent_missing(self, setup_sql):
        _, repo, pid = setup_sql
        # Create a delta snapshot with missing parent in DB
        snap = StateSnapshot(snapshot_id="delta", components={"_delta": {"diffs": []}}, is_checkpoint=False, parent_id="missing")
        repo.save_snapshot(pid, snap, is_checkpoint=False, parent_id="missing")
        
        # Should fallback to returning components as is (which is the diffs dict)
        fetched = repo.get_snapshot("delta")
        assert "_delta" in fetched.components

    def test_sql_reconstruct_snapshot_no_parent_id(self, setup_sql):
        _, repo, pid = setup_sql
        # Create a delta snapshot with NO parent_id (corrupt state)
        from gradio_chat_agent.persistence.models import Snapshot
        with repo.SessionLocal() as session:
            repo._ensure_project(pid)
            session.add(Snapshot(id="bad", project_id=pid, components={"_delta": {"diffs": []}}, is_checkpoint=False, parent_id=None))
            session.commit()
            
        fetched = repo.get_snapshot("bad")
        assert "_delta" in fetched.components

    def test_in_memory_save_snapshot_no_parent(self, setup_in_memory):
        _, repo, pid = setup_in_memory
        snap = StateSnapshot(snapshot_id="s1", components={"demo": {"v": 1}})
        # Save as delta but no parent exists or provided
        repo.save_snapshot(pid, snap, is_checkpoint=False, parent_id=None)
        assert repo.get_snapshot("s1").components == {"demo": {"v": 1}}

    def test_in_memory_reconstruct_parent_missing(self, setup_in_memory):
        _, repo, pid = setup_in_memory
        snap = StateSnapshot(snapshot_id="s1", components={"_delta": {"diffs": []}})
        repo._snapshots[pid] = [StateSnapshot(snapshot_id="s1", components={"_delta": {"diffs": []}}, is_checkpoint=False, parent_id="ghost")]
        
        res = repo.get_snapshot("s1")
        assert "_delta" in res.components

    def test_revert_creates_checkpoint(self, setup_sql):
        engine, repo, pid = setup_sql
        # Create a snapshot
        engine.execute_intent(pid, ChatIntent(type=IntentType.ACTION_CALL, request_id="r1", action_id="demo.counter.set", inputs={"value": 10}), user_roles=["admin"])
        snap_id = repo.get_latest_snapshot(pid).snapshot_id
        
        # Revert
        engine.revert_to_snapshot(pid, snap_id)
        
        latest = repo.get_latest_snapshot(pid)
        assert latest.is_checkpoint is True
        assert latest.parent_id is None

    def test_complex_state_diff_application(self):
        from gradio_chat_agent.utils import apply_state_diff
        from gradio_chat_agent.models.execution_result import StateDiffEntry
        from gradio_chat_agent.models.enums import StateDiffOp
        
        state = {"a": {"b": 1}}
        diffs = [
            StateDiffEntry(path="a.c", op=StateDiffOp.ADD, value=2),
            StateDiffEntry(path="x.y.z", op=StateDiffOp.ADD, value=3), # Auto-create parents
            StateDiffEntry(path="a.b", op=StateDiffOp.REPLACE, value=10),
            StateDiffEntry(path="a.c", op=StateDiffOp.REMOVE)
        ]
        
        new_state = apply_state_diff(state, diffs)
        assert new_state["a"]["b"] == 10
        assert "c" not in new_state["a"]
        assert new_state["x"]["y"]["z"] == 3
