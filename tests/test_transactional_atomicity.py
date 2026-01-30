import pytest
import uuid
from unittest.mock import MagicMock, patch
from gradio_chat_agent.persistence.in_memory import InMemoryStateRepository
from gradio_chat_agent.persistence.sql_repository import SQLStateRepository
from gradio_chat_agent.models.execution_result import ExecutionResult, ExecutionStatus
from gradio_chat_agent.models.state_snapshot import StateSnapshot
from gradio_chat_agent.execution.engine import ExecutionEngine
from gradio_chat_agent.registry.in_memory import InMemoryRegistry
from gradio_chat_agent.models.intent import ChatIntent
from gradio_chat_agent.models.enums import IntentType

class TestTransactionalAtomicity:
    def test_in_memory_save_execution_and_snapshot(self):
        repo = InMemoryStateRepository()
        pid = "p1"
        res = ExecutionResult(request_id="r1", action_id="a", status=ExecutionStatus.SUCCESS, state_snapshot_id="s1")
        snap = StateSnapshot(snapshot_id="s1", components={"c": {}})
        
        repo.save_execution_and_snapshot(pid, res, snap)
        
        assert repo.get_latest_snapshot(pid).snapshot_id == "s1"
        assert repo.get_execution_history(pid)[0].request_id == "r1"

    def test_sql_save_execution_and_snapshot(self):
        repo = SQLStateRepository("sqlite:///:memory:")
        pid = "p1"
        res = ExecutionResult(request_id="r1", action_id="a", status=ExecutionStatus.SUCCESS, state_snapshot_id="s1")
        snap = StateSnapshot(snapshot_id="s1", components={"c": {}})
        
        repo.save_execution_and_snapshot(pid, res, snap)
        
        assert repo.get_latest_snapshot(pid).snapshot_id == "s1"
        assert repo.get_execution_history(pid)[0].request_id == "r1"

    def test_sql_atomicity_rollback(self):
        repo = SQLStateRepository("sqlite:///:memory:")
        pid = "p1"
        
        # We need to force a failure during the transaction.
        # Let's mock session.add to fail on the second call (execution).
        
        from gradio_chat_agent.persistence.models import Execution
        
        original_session_local = repo.SessionLocal
        
        class FailingSession:
            def __init__(self, real_session):
                self.real_session = real_session
                self.add_count = 0
            def __enter__(self): return self
            def __exit__(self, exc_type, exc_val, exc_tb):
                self.real_session.close()
            def get(self, *args, **kwargs): return self.real_session.get(*args, **kwargs)
            def add(self, obj):
                self.add_count += 1
                if isinstance(obj, Execution):
                    raise RuntimeError("Simulated Database Error during Execution Save")
                self.real_session.add(obj)
            def commit(self): self.real_session.commit()
            def execute(self, *args, **kwargs): return self.real_session.execute(*args, **kwargs)

        repo.SessionLocal = lambda: FailingSession(original_session_local())
        
        res = ExecutionResult(request_id="r1", action_id="a", status=ExecutionStatus.SUCCESS, state_snapshot_id="s1")
        snap = StateSnapshot(snapshot_id="s1", components={"c": {}})
        
        with pytest.raises(RuntimeError, match="Simulated Database Error"):
            repo.save_execution_and_snapshot(pid, res, snap)
            
        # Verify that NOTHING was saved (Snapshot shouldn't be there either because of rollback)
        # We need a fresh repo or bypass the failing session to check
        repo.SessionLocal = original_session_local
        assert repo.get_latest_snapshot(pid) is None
        assert len(repo.get_execution_history(pid)) == 0

    def test_engine_uses_atomic_save(self):
        registry = InMemoryRegistry()
        repository = MagicMock()
        engine = ExecutionEngine(registry, repository)
        project_id = "p1"
        
        # Setup action
        registry.register_action(
            MagicMock(action_id="test.act", cost=1.0, permission=MagicMock(risk="low", confirmation_required=False, visibility="user"), input_schema={}, preconditions=[]),
            handler=lambda i, s: ({}, [], "ok")
        )
        
        intent = ChatIntent(type=IntentType.ACTION_CALL, request_id="r1", action_id="test.act")
        
        # We need to mock repository methods that are called before save_execution_and_snapshot
        repository.get_project_limits.return_value = {}
        repository.is_project_archived.return_value = False
        repository.get_latest_snapshot.return_value = None
        
        engine.execute_intent(project_id, intent, user_roles=["admin"])
        
        # Verify save_execution_and_snapshot was called instead of individual saves
        repository.save_execution_and_snapshot.assert_called_once()
        repository.save_snapshot.assert_not_called()
        repository.save_execution.assert_not_called()

    def test_engine_revert_uses_atomic_save(self):
        registry = InMemoryRegistry()
        repository = MagicMock()
        engine = ExecutionEngine(registry, repository)
        project_id = "p1"
        
        repository.get_snapshot.return_value = StateSnapshot(snapshot_id="target", components={})
        repository.get_latest_snapshot.return_value = None
        
        engine.revert_to_snapshot(project_id, "target")
        
        repository.save_execution_and_snapshot.assert_called_once()
        repository.save_snapshot.assert_not_called()
        repository.save_execution.assert_not_called()
