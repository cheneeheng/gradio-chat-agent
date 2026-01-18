import pytest
import threading
import time
from gradio_chat_agent.execution.engine import ExecutionEngine
from gradio_chat_agent.persistence.in_memory import InMemoryStateRepository
from gradio_chat_agent.persistence.sql_repository import SQLStateRepository
from gradio_chat_agent.registry.in_memory import InMemoryRegistry

class TestDistributedLocking:
    @pytest.fixture
    def setup_in_memory(self):
        repo = InMemoryStateRepository()
        engine = ExecutionEngine(InMemoryRegistry(), repo)
        return engine, repo

    @pytest.fixture
    def setup_sql(self):
        repo = SQLStateRepository("sqlite:///:memory:")
        engine = ExecutionEngine(InMemoryRegistry(), repo)
        return engine, repo

    def test_in_memory_lock_acquisition(self, setup_in_memory):
        engine, _ = setup_in_memory
        pid = "p1"
        
        with engine.project_lock(pid):
            # Try to acquire again with DIFFERENT holder (mocked by using another thread or just calling repo)
            # Actually, engine.project_lock generates holder_id using PID and thread ID.
            
            # Since we are in the same thread, engine.project_lock would succeed if we use it again 
            # (because of local threading.Lock re-entrancy if we used RLock, but it's regular Lock).
            # Wait, threading.Lock is NOT re-entrant.
            pass

    def test_sql_lock_acquisition(self, setup_sql):
        engine, repo = setup_sql
        pid = "p1"
        holder1 = "h1"
        holder2 = "h2"
        
        # 1. Acquire
        assert repo.acquire_lock(pid, holder1) is True
        
        # 2. Try to acquire by another holder
        assert repo.acquire_lock(pid, holder2) is False
        
        # 3. Release
        repo.release_lock(pid, holder1)
        
        # 4. Acquire by another holder
        assert repo.acquire_lock(pid, holder2) is True

    def test_lock_expiry(self, setup_sql):
        engine, repo = setup_sql
        pid = "p1"
        holder1 = "h1"
        holder2 = "h2"
        
        # Acquire with short timeout
        repo.acquire_lock(pid, holder1, timeout_seconds=1)
        
        # Wait for expiry
        time.sleep(1.1)
        
        # holder2 should be able to take it
        assert repo.acquire_lock(pid, holder2) is True

    def test_lock_timeout_exception(self, setup_in_memory):
        engine, repo = setup_in_memory
        pid = "p1"
        
        # Hold lock in a separate thread
        def hold():
            with engine.project_lock(pid):
                time.sleep(2)
        
        t = threading.Thread(target=hold)
        t.start()
        time.sleep(0.5)
        
        # Attempt to acquire with shorter timeout
        with pytest.raises(RuntimeError, match="Could not acquire local lock"):
            with engine.project_lock(pid, timeout=1):
                pass
        
        t.join()

    def test_sql_lock_race_condition(self, setup_sql):
        _, repo = setup_sql
        # Manually trigger the exception branch in acquire_lock
        from unittest.mock import patch, MagicMock
        
        mock_session_cls = MagicMock()
        mock_session = mock_session_cls.return_value.__enter__.return_value
        # Mock session.get to return None (so it tries to create)
        mock_session.get.return_value = None
        # Mock session.commit to raise Exception (simulating UniqueConstraint violation)
        mock_session.commit.side_effect = Exception("Race condition")
        
        with patch.object(repo, "SessionLocal", mock_session_cls):
            assert repo.acquire_lock("p1", "h1") is False

    def test_in_memory_lock_reentry_same_holder(self, setup_in_memory):
        _, repo = setup_in_memory
        pid = "p1"
        holder = "h1"
        
        assert repo.acquire_lock(pid, holder) is True
        # Same holder can re-acquire (renew)
        assert repo.acquire_lock(pid, holder) is True

    def test_in_memory_release_wrong_holder(self, setup_in_memory):
        _, repo = setup_in_memory
        pid = "p1"
        repo.acquire_lock(pid, "h1")
        # Try release by h2
        repo.release_lock(pid, "h2")
        # Still held by h1
        assert repo.acquire_lock(pid, "h3") is False

    def test_in_memory_release_no_locks(self, setup_in_memory):
        _, repo = setup_in_memory
        # Should not crash
        repo.release_lock("p1", "h1")
