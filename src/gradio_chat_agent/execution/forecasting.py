"""Service for predicting budget exhaustion based on historical usage."""

from datetime import datetime, timezone, timedelta
from typing import Any, Optional

from gradio_chat_agent.execution.engine import ExecutionEngine
from gradio_chat_agent.observability.logging import get_logger

logger = get_logger(__name__)


class ForecastingService:
    """Predicts budget exhaustion for projects."""

    def __init__(self, engine: ExecutionEngine):
        """Initializes the forecasting service.

        Args:
            engine: The authoritative execution engine.
        """
        self.engine = engine

    def get_budget_forecast(self, project_id: str) -> dict[str, Any]:
        """Calculates budget usage stats and exhaustion predictions.

        Args:
            project_id: The ID of the project.

        Returns:
            A dictionary with forecast data.
        """
        limits = self.engine.repository.get_project_limits(project_id)
        daily_limit = limits.get("limits", {}).get("budget", {}).get("daily")
        
        if daily_limit is None:
            return {"status": "no_limit", "message": "No daily budget limit set for this project."}

        # Fetch usage for the last 24 hours
        current_usage = self.engine.repository.get_daily_budget_usage(project_id)
        
        # Calculate burn rate (units per hour)
        # We look at the last few hours to estimate current pace
        history = self.engine.repository.get_execution_history(project_id, limit=100)
        
        now = datetime.now(timezone.utc)
        start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
        
        successful_today = [
            e for e in history 
            if e.status == "success" and e.timestamp.replace(tzinfo=timezone.utc if e.timestamp.tzinfo is None else e.timestamp.tzinfo) >= start_of_day
        ]
        
        if not successful_today:
            return {
                "status": "ok",
                "current_usage": current_usage,
                "daily_limit": daily_limit,
                "burn_rate_per_hour": 0.0,
                "estimated_exhaustion_at": None
            }

        # Time elapsed since start of day in hours
        hours_elapsed = (now - start_of_day).total_seconds() / 3600.0
        if hours_elapsed < 0.1: # Avoid division by zero very early in the day
            hours_elapsed = 0.1
            
        burn_rate = current_usage / hours_elapsed
        
        remaining_budget = daily_limit - current_usage
        
        if remaining_budget <= 0:
            return {
                "status": "exhausted",
                "current_usage": current_usage,
                "daily_limit": daily_limit,
                "burn_rate_per_hour": burn_rate,
                "estimated_exhaustion_at": now.isoformat()
            }
            
        if burn_rate <= 0:
            return {
                "status": "ok",
                "current_usage": current_usage,
                "daily_limit": daily_limit,
                "burn_rate_per_hour": 0.0,
                "estimated_exhaustion_at": None
            }

        hours_to_exhaustion = remaining_budget / burn_rate
        exhaustion_time = now + timedelta(hours=hours_to_exhaustion)
        
        # If exhaustion is predicted after the end of the day, it's 'ok'
        end_of_day = start_of_day + timedelta(days=1)
        if exhaustion_time > end_of_day:
            return {
                "status": "ok",
                "current_usage": current_usage,
                "daily_limit": daily_limit,
                "burn_rate_per_hour": burn_rate,
                "estimated_exhaustion_at": None
            }

        return {
            "status": "warning",
            "current_usage": current_usage,
            "daily_limit": daily_limit,
            "burn_rate_per_hour": burn_rate,
            "estimated_exhaustion_at": exhaustion_time.isoformat()
        }
