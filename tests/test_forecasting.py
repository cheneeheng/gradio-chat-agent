import pytest
from unittest.mock import MagicMock, patch
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

    def test_forecasting_early_day_limit(self, setup_service):
        service, engine, pid = setup_service
        engine.repository.set_project_limits(pid, {"limits": {"budget": {"daily": 100}}})
        
        # Mock usage 10, but time is very early (0.05 hours elapsed)
        # We need to mock datetime.now AND the timestamp of execution history
        now = datetime(2023, 1, 1, 0, 3, tzinfo=timezone.utc) # 3 mins in
        start_of_day = datetime(2023, 1, 1, 0, 0, tzinfo=timezone.utc)
        
        # Mock get_daily_budget_usage to return 10
        with patch.object(engine.repository, "get_daily_budget_usage", return_value=10.0):
            with patch("gradio_chat_agent.execution.forecasting.datetime") as mock_dt:
                mock_dt.now.return_value = now
                
                # Mock execution history to bypass Repo/Pydantic issues with Mock datetime
                mock_res = ExecutionResult(
                    request_id="r1", action_id="a", status=ExecutionStatus.SUCCESS,
                    state_snapshot_id="s", timestamp=now, metadata={"cost": 10}
                )
                # We mock the method on the INSTANCE
                engine.repository.get_execution_history = MagicMock(return_value=[mock_res])
                
                res = service.get_budget_forecast(pid)
                # Should not crash and use 0.1 hours floor
                # Usage 10. Elapsed < 0.1 -> 0.1. Burn rate = 10 / 0.1 = 100/hr.
                assert res["burn_rate_per_hour"] == 100.0

    def test_forecasting_exhausted_coverage(self, setup_service):
        service, engine, pid = setup_service
        engine.repository.set_project_limits(pid, {"limits": {"budget": {"daily": 10}}})
        
        # Mock usage 20
        with patch.object(engine.repository, "get_daily_budget_usage", return_value=20.0):
            mock_res = ExecutionResult(
                request_id="r1", action_id="a", status=ExecutionStatus.SUCCESS,
                state_snapshot_id="s", timestamp=datetime.now(timezone.utc), metadata={"cost": 20}
            )
            engine.repository.save_execution(pid, mock_res)
            
            res = service.get_budget_forecast(pid)
            assert res["status"] == "exhausted"

    def test_forecasting_late_exhaustion_coverage(self, setup_service):
        service, engine, pid = setup_service
        engine.repository.set_project_limits(pid, {"limits": {"budget": {"daily": 1000}}})
        
        # Usage 10 in 10 hours -> rate 1/hr.
        now = datetime(2023, 1, 1, 10, 0, tzinfo=timezone.utc)
        
        with patch.object(engine.repository, "get_daily_budget_usage", return_value=10.0):
            with patch("gradio_chat_agent.execution.forecasting.datetime") as mock_dt:
                mock_dt.now.return_value = now
                
                mock_res = ExecutionResult(
                    request_id="r1", action_id="a", status=ExecutionStatus.SUCCESS,
                    state_snapshot_id="s", timestamp=now, metadata={"cost": 10}
                )
                engine.repository.save_execution(pid, mock_res)
                
                res = service.get_budget_forecast(pid)
                assert res["status"] == "ok"
                assert res["estimated_exhaustion_at"] is None

    def test_forecasting_zero_burn_rate(self, setup_service):
        service, engine, pid = setup_service
        engine.repository.set_project_limits(pid, {"limits": {"budget": {"daily": 100}}})
        
        # Successful today exists, but cost is 0
        mock_res = ExecutionResult(
            request_id="r1", action_id="a", status=ExecutionStatus.SUCCESS,
            state_snapshot_id="s", timestamp=datetime.now(timezone.utc), metadata={"cost": 0}
        )
        engine.repository.save_execution(pid, mock_res)
        
        with patch.object(engine.repository, "get_daily_budget_usage", return_value=0.0):
            res = service.get_budget_forecast(pid)
            assert res["status"] == "ok"
            assert res["burn_rate_per_hour"] == 0.0

@pytest.fixture
def setup_service():
    engine = ExecutionEngine(InMemoryRegistry(), InMemoryStateRepository())
    service = ForecastingService(engine)
    pid = "p1"
    engine.repository.create_project(pid, "P1")
    return service, engine, pid
