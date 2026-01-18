import pytest
import time
from unittest.mock import MagicMock, patch
from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock, patch
from gradio_chat_agent.execution.observer import AuditLogObserver
from gradio_chat_agent.execution.engine import ExecutionEngine
from gradio_chat_agent.persistence.in_memory import InMemoryStateRepository
from gradio_chat_agent.registry.in_memory import InMemoryRegistry
from gradio_chat_agent.models.execution_result import ExecutionResult
from gradio_chat_agent.models.enums import ExecutionStatus

class TestAsyncObserver:
    @pytest.fixture
    def setup(self):
        registry = InMemoryRegistry()
        repository = InMemoryStateRepository()
        engine = ExecutionEngine(registry, repository)
        observer = AuditLogObserver(engine, poll_interval=0.1)
        project_id = "p1"
        repository.create_project(project_id, "P1")
        return observer, engine, repository, project_id

    def test_observer_detects_success(self, setup):
        observer, engine, repo, pid = setup
        callback = MagicMock()
        observer.add_callback(callback)
        
        # We need to set the timestamp to slightly in the past so the observer sees it
        # Actually start() sets it to 'now'.
        observer.start()
        
        # Give it a tiny bit of time
        time.sleep(0.2)
        
        # Add a successful execution
        res = ExecutionResult(
            request_id="r1", action_id="a1", status=ExecutionStatus.SUCCESS, 
            state_snapshot_id="s1", timestamp=datetime.now(timezone.utc) + timedelta(seconds=1)
        )
        repo.save_execution(pid, res)
        
        # Poll manually or wait
        observer._poll_and_process()
        
        callback.assert_called_once()
        observer.stop()

    def test_observer_ignores_failures(self, setup):
        observer, engine, repo, pid = setup
        callback = MagicMock()
        observer.add_callback(callback)
        observer.start()
        
        res = ExecutionResult(
            request_id="r1", action_id="a1", status=ExecutionStatus.FAILED, 
            state_snapshot_id="s1", timestamp=datetime.now(timezone.utc) + timedelta(seconds=1)
        )
        repo.save_execution(pid, res)
        
        observer._poll_and_process()
        callback.assert_not_called()
        observer.stop()

    def test_observer_callback_exception_handling(self, setup):
        observer, engine, repo, pid = setup
        callback = MagicMock(side_effect=Exception("Callback crashed"))
        observer.add_callback(callback)
        observer.start()
        
        res = ExecutionResult(
            request_id="r1", action_id="a1", status=ExecutionStatus.SUCCESS, 
            state_snapshot_id="s1", timestamp=datetime.now(timezone.utc) + timedelta(seconds=1)
        )
        repo.save_execution(pid, res)
        
        # Should not raise exception
        observer._poll_and_process()
        callback.assert_called_once()
        observer.stop()

    def test_observer_lifecycle(self, setup):
        observer, _, _, _ = setup
        with patch.object(observer, "_run") as mock_run:
            observer.start()
            assert observer._thread is not None
            observer.stop()
            assert observer._thread is None

    def test_observer_double_start(self, setup):
        observer, _, _, _ = setup
        observer.start()
        t1 = observer._thread
        observer.start()
        assert observer._thread is t1
        observer.stop()

    def test_observer_run_exception(self, setup):
        observer, _, _, _ = setup
        observer.poll_interval = 0.01
        
        # Mock poll_and_process to raise once then succeed (or just raise)
        observer._poll_and_process = MagicMock(side_effect=[Exception("Poll error"), None])
        
        # Run briefly
        observer.start()
        time.sleep(0.1)
        observer.stop()
        
        assert observer._poll_and_process.call_count >= 1

    def test_observer_timestamp_logic(self, setup):
        observer, engine, repo, pid = setup
        
        # 1. Start (sets last_processed to now)
        observer.start()
        # Mock last_processed to be in the past
        observer._last_processed_timestamp = datetime(2020, 1, 1, tzinfo=timezone.utc)
        
        # 2. Add new execution (naive timestamp)
        mock_res = ExecutionResult(
            request_id="r1", action_id="a", status=ExecutionStatus.SUCCESS,
            state_snapshot_id="s", timestamp=datetime(2021, 1, 1), # Naive
            metadata={}
        )
        repo.save_execution(pid, mock_res)
        
        # 3. Poll
        callback = MagicMock()
        observer.add_callback(callback)
        observer._poll_and_process()
        
        # Should have called callback
        callback.assert_called_once()
        # Should have updated timestamp (aware)
        assert observer._last_processed_timestamp.year == 2021
        assert observer._last_processed_timestamp.tzinfo is not None
        
        observer.stop()
