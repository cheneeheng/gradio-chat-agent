"""Operational alerting system for the Gradio Chat Agent."""

from typing import Any, Optional, Callable
from gradio_chat_agent.models.enums import ExecutionStatus
from gradio_chat_agent.observability.logging import get_logger

logger = get_logger(__name__)


class AlertingService:
    """Monitors system performance and triggers alerts for anomalies."""

    def __init__(self, engine):
        """Initializes the alerting service.

        Args:
            engine: The authoritative execution engine.
        """
        self.engine = engine
        self._handlers: list[Callable[[dict[str, Any]], None]] = []
        
        # Default handler: log to INFO
        self.add_handler(self._log_handler)

    def add_handler(self, handler: Callable[[dict[str, Any]], None]):
        """Registers an alert handler (e.g. a webhook dispatcher)."""
        self._handlers.append(handler)

    def _log_handler(self, alert: dict[str, Any]):
        logger.info(f"ALERT: {alert.get('message')}", extra={"extra_fields": {"event": "alert_triggered", "alert": alert}})

    def check_execution_alerts(self, project_id: str, result):
        """Checks for alerts related to a specific execution result.

        Args:
            project_id: The project ID.
            result: The execution result.
        """
        # 1. Failure Rate check (Last 5 minutes)
        total_5m = self.engine.repository.count_recent_executions(project_id, minutes=5)
        if total_5m >= 10: # Minimum sample size
            failed_5m = self.engine.repository.count_recent_executions(project_id, minutes=5, status=ExecutionStatus.FAILED)
            failure_rate = failed_5m / total_5m
            if failure_rate > 0.05:
                self._trigger_alert({
                    "type": "high_failure_rate",
                    "project_id": project_id,
                    "failure_rate": failure_rate,
                    "message": f"High failure rate detected for project {project_id}: {failure_rate:.1%}"
                })

        # 2. LLM Latency check
        if result.execution_time_ms and result.execution_time_ms > 10000:
            self._trigger_alert({
                "type": "high_latency",
                "project_id": project_id,
                "latency_ms": result.execution_time_ms,
                "action_id": result.action_id,
                "message": f"High latency detected for action {result.action_id} in project {project_id}: {result.execution_time_ms:.0f}ms"
            })

        # 3. Budget Exhaustion check
        limits = self.engine.repository.get_project_limits(project_id)
        daily_limit = limits.get("limits", {}).get("budget", {}).get("daily")
        if daily_limit:
            usage = self.engine.repository.get_daily_budget_usage(project_id)
            usage_ratio = usage / daily_limit
            
            thresholds = [1.0, 0.9, 0.8]
            for t in thresholds:
                # We want to trigger only once per threshold transition
                # For simplicity, we just trigger if it's ABOVE but we should ideally track last state
                if usage_ratio >= t:
                    self._trigger_alert({
                        "type": "budget_exhaustion",
                        "project_id": project_id,
                        "usage_ratio": usage_ratio,
                        "threshold": t,
                        "message": f"Budget threshold {t:.0%} reached for project {project_id} (Usage: {usage}/{daily_limit})"
                    })
                    break # Only trigger highest threshold

    def _trigger_alert(self, alert: dict[str, Any]):
        """Dispatches an alert to all registered handlers."""
        for handler in self._handlers:
            try:
                handler(alert)
            except Exception as e:
                logger.error(f"Error in alert handler: {str(e)}")
