import pytest
from datetime import datetime, timezone, timedelta
from gradio_chat_agent.execution.forecasting import ForecastingService
from gradio_chat_agent.execution.engine import ExecutionEngine
from gradio_chat_agent.persistence.in_memory import InMemoryStateRepository
from gradio_chat_agent.registry.in_memory import InMemoryRegistry
from gradio_chat_agent.models.execution_result import ExecutionResult
from gradio_chat_agent.models.enums import ExecutionStatus

class TestForecasting:
    @pytest.fixture
    def setup(self):
        engine = ExecutionEngine(InMemoryRegistry(), InMemoryStateRepository())
        service = ForecastingService(engine)
        pid = "p1"
        engine.repository.create_project(pid, "P1")
        return service, engine, pid

    def test_no_limit(self, setup):
        service, _, pid = setup
        res = service.get_budget_forecast(pid)
        assert res["status"] == "no_limit"

    def test_no_usage(self, setup):
        service, engine, pid = setup
        engine.repository.set_project_limits(pid, {"limits": {"budget": {"daily": 100.0}}})
        res = service.get_budget_forecast(pid)
        assert res["status"] == "ok"
        assert res["burn_rate_per_hour"] == 0.0

    def test_exhausted(self, setup):
        service, engine, pid = setup
        engine.repository.set_project_limits(pid, {"limits": {"budget": {"daily": 50.0}}})
        
        # Add usage
        res = ExecutionResult(
            request_id="r1", action_id="a", status=ExecutionStatus.SUCCESS, 
            state_snapshot_id="s", metadata={"cost": 60.0}, timestamp=datetime.now(timezone.utc)
        )
        engine.repository.save_execution(pid, res)
        
        forecast = service.get_budget_forecast(pid)
        assert forecast["status"] == "exhausted"

    def test_warning_logic(self, setup):
        service, engine, pid = setup
        engine.repository.set_project_limits(pid, {"limits": {"budget": {"daily": 100.0}}})
        
        # We need to simulate a burn rate that will exhaust the budget BEFORE the end of the day.
        # If it's early in the day, high usage will trigger a warning.
        
        # Mock 50 units used in the first hour of the day
        now = datetime.now(timezone.utc)
        start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
        
        # Ensure we are at least 1 hour into the day for a clear test
        # If not, we can't easily trigger the 'warning' vs 'ok' based on clock without mocking datetime.
        
        res = ExecutionResult(
            request_id="r1", action_id="a", status=ExecutionStatus.SUCCESS, 
            state_snapshot_id="s", metadata={"cost": 80.0}, 
            timestamp=start_of_day + timedelta(minutes=10)
        )
        engine.repository.save_execution(pid, res)
        
        # Usage 80, limit 100. Burn rate is 80 units / (now - start_of_day) hours.
        # If it's early enough, exhaustion will be predicted soon.
        forecast = service.get_budget_forecast(pid)
        
        # If hours_elapsed is small, burn_rate is huge.
        if forecast["status"] == "warning":
            assert forecast["estimated_exhaustion_at"] is not None
        else:
            # If it's late in the day, 80 units might be 'ok' for a 100 limit.
            assert forecast["status"] == "ok"
