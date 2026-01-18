import pytest
from unittest.mock import MagicMock, patch
from gradio_chat_agent.execution.scheduler import SchedulerWorker
from gradio_chat_agent.execution.engine import ExecutionEngine
from gradio_chat_agent.persistence.in_memory import InMemoryStateRepository
from gradio_chat_agent.registry.in_memory import InMemoryRegistry

class TestTaskRetries:
    @pytest.fixture
    def setup(self):
        engine = ExecutionEngine(InMemoryRegistry(), InMemoryStateRepository())
        worker = SchedulerWorker(engine)
        return worker, engine

    def test_scheduler_retries_on_failure(self, setup):
        worker, engine = setup
        
        # Mock engine to return failure
        mock_res = MagicMock(status="failed", message="Err")
        engine.execute_intent = MagicMock(return_value=mock_res)
        
        with patch("time.sleep"): # Fast tests
            worker._execute_scheduled_action({
                "id": "s1", "project_id": "p1", "action_id": "a"
            })
            
        # Should have called execute_intent 3 times
        assert engine.execute_intent.call_count == 3

    def test_scheduler_stops_on_success(self, setup):
        worker, engine = setup
        
        # Mock engine to return success on 2nd attempt
        res_fail = MagicMock(status="failed")
        res_ok = MagicMock(status="success", message="OK")
        engine.execute_intent = MagicMock(side_effect=[res_fail, res_ok])
        
        with patch("time.sleep"):
            worker._execute_scheduled_action({
                "id": "s1", "project_id": "p1", "action_id": "a"
            })
            
        assert engine.execute_intent.call_count == 2

    def test_scheduler_retries_on_exception(self, setup):
        worker, engine = setup
        
        engine.execute_intent = MagicMock(side_effect=ValueError("Boom"))
        
        with patch("time.sleep"):
            worker._execute_scheduled_action({
                "id": "s1", "project_id": "p1", "action_id": "a"
            })
            
        assert engine.execute_intent.call_count == 3
