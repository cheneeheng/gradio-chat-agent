import time
import pytest
from unittest.mock import MagicMock, patch
from gradio_chat_agent.execution.scheduler import SchedulerWorker
from gradio_chat_agent.execution.engine import ExecutionEngine
from gradio_chat_agent.persistence.in_memory import InMemoryStateRepository
from gradio_chat_agent.registry.in_memory import InMemoryRegistry
from gradio_chat_agent.models.enums import ExecutionStatus

class TestSchedulerWorker:
    @pytest.fixture
    def setup(self):
        registry = InMemoryRegistry()
        repository = InMemoryStateRepository()
        engine = ExecutionEngine(registry, repository)
        # Use short poll interval for testing
        worker = SchedulerWorker(engine, poll_interval=0.1)
        return worker, engine, repository

    def test_worker_sync_schedules(self, setup):
        worker, engine, repo = setup
        
        # 1. Add a schedule to repo
        schedule_id = "s1"
        repo.save_schedule({
            "id": schedule_id,
            "project_id": "p1",
            "action_id": "demo.act",
            "cron": "* * * * *",
            "enabled": True
        })
        
        # 2. Sync
        worker._sync_schedules()
        assert schedule_id in worker._active_schedules
        assert worker.scheduler.get_job(schedule_id) is not None
        
        # 3. Disable schedule
        repo.save_schedule({
            "id": schedule_id,
            "project_id": "p1",
            "action_id": "demo.act",
            "cron": "* * * * *",
            "enabled": False
        })
        worker._sync_schedules()
        assert schedule_id not in worker._active_schedules
        assert worker.scheduler.get_job(schedule_id) is None

    def test_execute_scheduled_action(self, setup):
        worker, engine, repo = setup
        
        # Mock engine.execute_intent
        engine.execute_intent = MagicMock(return_value=MagicMock(status="success", message="OK"))
        
        config = {
            "id": "s1",
            "project_id": "p1",
            "action_id": "act.1",
            "inputs": {"val": 1}
        }
        
        worker._execute_scheduled_action(config)
        
        # Verify engine was called with correct context
        engine.execute_intent.assert_called_once()
        args, kwargs = engine.execute_intent.call_args
        assert kwargs["project_id"] == "p1"
        assert kwargs["intent"].action_id == "act.1"
        assert kwargs["intent"].inputs == {"val": 1}
        assert kwargs["user_id"] == "system_scheduler"
        assert "admin" in kwargs["user_roles"]

    def test_worker_lifecycle(self, setup):
        worker, _, _ = setup
        
        with patch.object(worker, "_run") as mock_run:
            worker.start()
            assert worker._thread is not None
            worker.stop()
            assert worker._thread is None
            assert worker.scheduler.running is False

    def test_execute_scheduled_action_failure(self, setup):
        worker, engine, _ = setup
        engine.execute_intent = MagicMock(return_value=MagicMock(status="failed", message="Err"))
        
        # Should not raise exception
        worker._execute_scheduled_action({
            "id": "s1", "project_id": "p1", "action_id": "a", "inputs": {}
        })

    def test_execute_scheduled_action_exception(self, setup):
        worker, engine, _ = setup
        engine.execute_intent = MagicMock(side_effect=ValueError("Boom"))
        
        # Should not raise exception
        worker._execute_scheduled_action({
            "id": "s1", "project_id": "p1", "action_id": "a", "inputs": {}
        })

    def test_worker_run_loop_exception(self, setup):
        worker, _, _ = setup
        # Force exception in sync
        worker._sync_schedules = MagicMock(side_effect=RuntimeError("Sync error"))
        
        # We'll run it once and stop
        with patch.object(worker._stop_event, "is_set", side_effect=[False, True]):
            worker._run()
            # If it didn't crash, it caught the error
            worker._sync_schedules.assert_called_once()

    def test_scheduler_double_start(self, setup):
        worker, _, _ = setup
        worker.start()
        t1 = worker._thread
        worker.start()
        assert worker._thread is t1
        worker.stop()
