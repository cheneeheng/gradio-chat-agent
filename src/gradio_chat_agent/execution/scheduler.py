"""Background worker for executing scheduled tasks."""

import uuid
import threading
import time
from typing import Any, Optional

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from gradio_chat_agent.execution.engine import ExecutionEngine
from gradio_chat_agent.models.enums import ExecutionMode, IntentType
from gradio_chat_agent.models.intent import ChatIntent
from gradio_chat_agent.observability.logging import get_logger

logger = get_logger(__name__)


class SchedulerWorker:
    """Worker that polls for and executes scheduled actions."""

    def __init__(self, engine: ExecutionEngine, poll_interval: int = 60):
        """Initializes the scheduler worker.

        Args:
            engine: The authoritative execution engine.
            poll_interval: How often to poll for schedule updates (seconds).
        """
        self.engine = engine
        self.poll_interval = poll_interval
        self.scheduler = BackgroundScheduler()
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._active_schedules: set[str] = set()

    def start(self):
        """Starts the scheduler and the polling thread."""
        if self._thread is not None:
            return

        self.scheduler.start()
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        logger.info("Scheduler worker started.")

    def stop(self):
        """Stops the scheduler and the polling thread."""
        self._stop_event.set()
        self.scheduler.shutdown()
        if self._thread:
            self._thread.join()
            self._thread = None
        logger.info("Scheduler worker stopped.")

    def _run(self):
        """Main polling loop."""
        while not self._stop_event.is_set():
            try:
                self._sync_schedules()
            except Exception as e:
                logger.exception(f"Error syncing schedules: {str(e)}")
            
            # Wait for poll interval or stop event
            self._stop_event.wait(self.poll_interval)

    def _sync_schedules(self):
        """Synchronizes internal APScheduler jobs with the database."""
        enabled_schedules = self.engine.repository.list_enabled_schedules()
        enabled_ids = {s["id"] for s in enabled_schedules}

        # Remove jobs that are no longer enabled
        for job_id in list(self._active_schedules):
            if job_id not in enabled_ids:
                self.scheduler.remove_job(job_id)
                self._active_schedules.remove(job_id)
                logger.info(f"Removed schedule job: {job_id}")

        # Add or update jobs
        for s in enabled_schedules:
            job_id = s["id"]
            if job_id not in self._active_schedules:
                self.scheduler.add_job(
                    self._execute_scheduled_action,
                    CronTrigger.from_crontab(s["cron"]),
                    id=job_id,
                    args=[s],
                    replace_existing=True
                )
                self._active_schedules.add(job_id)
                logger.info(f"Added schedule job: {job_id} (Cron: {s['cron']})")

    def _execute_scheduled_action(self, schedule_config: dict[str, Any]):
        """Callback executed by APScheduler."""
        project_id = schedule_config["project_id"]
        action_id = schedule_config["action_id"]
        inputs = schedule_config.get("inputs", {})

        logger.info(f"Triggering scheduled action: {action_id} for project {project_id}")

        intent = ChatIntent(
            type=IntentType.ACTION_CALL,
            request_id=f"sched-{uuid.uuid4().hex[:8]}",
            action_id=action_id,
            inputs=inputs,
            execution_mode=ExecutionMode.AUTONOMOUS,
            confirmed=True, # System triggers are implicitly confirmed
            trace={"trigger": "schedule", "schedule_id": schedule_config["id"]}
        )

        try:
            # Execute as a "System" user with Admin privileges
            result = self.engine.execute_intent(
                project_id=project_id,
                intent=intent,
                user_roles=["admin"],
                user_id="system_scheduler"
            )
            
            if result.status == "success":
                logger.info(f"Scheduled action {action_id} completed successfully: {result.message}")
            else:
                logger.warning(f"Scheduled action {action_id} failed/rejected: {result.message}")
        except Exception as e:
            logger.exception(f"Unexpected error executing scheduled action {action_id}: {str(e)}")
