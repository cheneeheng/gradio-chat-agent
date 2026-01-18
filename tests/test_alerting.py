import pytest
from unittest.mock import MagicMock, patch
from gradio_chat_agent.execution.engine import ExecutionEngine
from gradio_chat_agent.observability.alerting import AlertingService
from gradio_chat_agent.persistence.in_memory import InMemoryStateRepository
from gradio_chat_agent.registry.in_memory import InMemoryRegistry
from gradio_chat_agent.models.enums import ExecutionStatus
from gradio_chat_agent.models.execution_result import ExecutionResult

class TestAlertingSystem:
    @pytest.fixture
    def setup(self):
        registry = InMemoryRegistry()
        repository = InMemoryStateRepository()
        engine = ExecutionEngine(registry, repository)
        service = AlertingService(engine)
        project_id = "test-alert"
        repository.create_project(project_id, "Test")
        return service, engine, repository, project_id

    def test_budget_exhaustion_alert(self, setup):
        service, _, repo, pid = setup
        handler = MagicMock()
        service.add_handler(handler)
        
        repo.set_project_limits(pid, {"limits": {"budget": {"daily": 100.0}}})
        
        # Success with 85% usage
        res = MagicMock(status=ExecutionStatus.SUCCESS, execution_time_ms=100, action_id="a")
        # Pre-set usage in repo
        repo.save_execution(pid, ExecutionResult(request_id="r1", action_id="a", status=ExecutionStatus.SUCCESS, state_snapshot_id="s1", metadata={"cost": 85.0}))
        
        service.check_execution_alerts(pid, res)
        
        handler.assert_called_once()
        alert = handler.call_args[0][0]
        assert alert["type"] == "budget_exhaustion"
        assert alert["threshold"] == 0.8

    def test_high_latency_alert(self, setup):
        service, _, _, pid = setup
        handler = MagicMock()
        service.add_handler(handler)
        
        res = MagicMock(status=ExecutionStatus.SUCCESS, execution_time_ms=12000, action_id="slow.act")
        service.check_execution_alerts(pid, res)
        
        handler.assert_called_once()
        alert = handler.call_args[0][0]
        assert alert["type"] == "high_latency"
        assert "slow.act" in alert["message"]

    def test_high_failure_rate_alert(self, setup):
        service, engine, repo, pid = setup
        handler = MagicMock()
        service.add_handler(handler)
        
        # Need 10 executions total. Let's add 10 failures.
        for i in range(10):
            repo.save_execution(pid, ExecutionResult(request_id=f"f{i}", action_id="a", status=ExecutionStatus.FAILED, state_snapshot_id="s"))
            
        res = MagicMock(status=ExecutionStatus.SUCCESS, execution_time_ms=100, action_id="a")
        service.check_execution_alerts(pid, res)
        
        handler.assert_called_once()
        alert = handler.call_args[0][0]
        assert alert["type"] == "high_failure_rate"

    def test_alert_handler_exception_handling(self, setup):
        service, _, _, pid = setup
        handler = MagicMock(side_effect=Exception("Handler crashed"))
        service.add_handler(handler)
        
        # Trigger high latency alert
        res = MagicMock(status=ExecutionStatus.SUCCESS, execution_time_ms=15000, action_id="a")
        # Should not crash
        service.check_execution_alerts(pid, res)
        handler.assert_called_once()

    def test_log_handler_coverage(self, setup):
        service, _, _, pid = setup
        # _log_handler is registered by default. 
        # We just need to trigger an alert and verify it doesn't crash and logs.
        res = MagicMock(status=ExecutionStatus.SUCCESS, execution_time_ms=15000, action_id="a")
        with patch("gradio_chat_agent.observability.alerting.logger") as mock_logger:
            service.check_execution_alerts(pid, res)
            mock_logger.info.assert_called()

    def test_budget_exhaustion_no_limit(self, setup):
        service, _, repo, pid = setup
        handler = MagicMock()
        service.add_handler(handler)
        
        repo.set_project_limits(pid, {}) # No budget limit
        res = MagicMock(status=ExecutionStatus.SUCCESS, execution_time_ms=100, action_id="a")
        service.check_execution_alerts(pid, res)
        handler.assert_not_called()

    def test_failure_rate_small_sample(self, setup):
        service, _, repo, pid = setup
        handler = MagicMock()
        service.add_handler(handler)
        
        # Only 5 failures (limit is 10)
        for i in range(5):
            repo.save_execution(pid, ExecutionResult(request_id=f"f{i}", action_id="a", status=ExecutionStatus.FAILED, state_snapshot_id="s"))
            
        res = MagicMock(status=ExecutionStatus.SUCCESS, execution_time_ms=100, action_id="a")
        service.check_execution_alerts(pid, res)
        handler.assert_not_called()
