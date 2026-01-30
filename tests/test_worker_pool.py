import pytest
import os
from unittest.mock import MagicMock, patch
from gradio_chat_agent.execution.tasks import execute_background_action, get_engine
from gradio_chat_agent.execution.scheduler import SchedulerWorker
from gradio_chat_agent.api.endpoints import ApiEndpoints

class TestWorkerPool:
    def test_execute_background_action_task(self, tmp_path):
        # Mock engine
        mock_engine = MagicMock()
        with patch("gradio_chat_agent.execution.tasks.get_engine", return_value=mock_engine):
            execute_background_action.call_local("p1", "a1", {"v": 1}, "u1", "test")
            
            mock_engine.execute_intent.assert_called_once()
            args, kwargs = mock_engine.execute_intent.call_args
            assert kwargs["project_id"] == "p1"
            assert kwargs["user_id"] == "u1"
            assert kwargs["intent"].action_id == "a1"

    def test_scheduler_offloads_to_huey(self):
        mock_engine = MagicMock()
        worker = SchedulerWorker(mock_engine, use_huey=True)
        
        with patch("gradio_chat_agent.execution.tasks.execute_background_action") as mock_bg:
            worker._execute_scheduled_action({
                "id": "s1", "project_id": "p1", "action_id": "a", "inputs": {"i": 1}
            })
            
            mock_bg.assert_called_once_with("p1", "a", {"i": 1}, "system_scheduler", "schedule")

    def test_api_webhook_offloads_to_huey(self):
        mock_engine = MagicMock()
        api = ApiEndpoints(mock_engine)
        
        # Mock webhook lookup
        mock_engine.repository.get_webhook.return_value = {
            "id": "wh1", "project_id": "p1", "action_id": "a", "secret": "s", "enabled": True
        }
        
        with patch("gradio_chat_agent.execution.tasks.execute_background_action") as mock_bg:
            # We need to pass correct signature
            import hmac, hashlib, json
            payload = {"val": 1}
            sig = hmac.new(b"s", json.dumps(payload, sort_keys=True).encode("utf-8"), hashlib.sha256).hexdigest()
            
            api.webhook_execute("wh1", payload, sig, use_huey=True)
            
            mock_bg.assert_called_once()
            args = mock_bg.call_args[0]
            assert args[0] == "p1"
            assert args[1] == "a"

    def test_get_engine_initialization(self, tmp_path):
        # Test the lazy initialization of get_engine
        with patch("gradio_chat_agent.execution.tasks.SQLStateRepository"), \
             patch("gradio_chat_agent.app.create_registry"), \
             patch("gradio_chat_agent.execution.tasks.ExecutionEngine") as mock_engine_cls:
            
            from gradio_chat_agent.execution import tasks
            tasks._engine = None # Reset
            
            engine = get_engine()
            assert engine == mock_engine_cls.return_value
            
            # Second call should return same instance
            assert get_engine() == engine
