"""Background observer for successful state mutations."""

import threading
import time
from typing import Callable, Optional

from gradio_chat_agent.execution.engine import ExecutionEngine
from gradio_chat_agent.models.execution_result import ExecutionResult
from gradio_chat_agent.observability.logging import get_logger

logger = get_logger(__name__)


class AuditLogObserver:
    """Observer that polls the audit log for successful mutations.

    This allows triggering long-running or unreliable external tasks
    asynchronously without blocking the main execution flow.
    """

    def __init__(
        self,
        engine: ExecutionEngine,
        poll_interval: float = 5.0,
        batch_size: int = 50,
    ):
        """Initializes the audit log observer.

        Args:
            engine: The authoritative execution engine.
            poll_interval: How often to poll for new log entries (seconds).
            batch_size: Number of entries to process in one poll.
        """
        self.engine = engine
        self.poll_interval = poll_interval
        self.batch_size = batch_size
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._callbacks: list[Callable[[str, ExecutionResult], None]] = []
        
        # Track the last processed sequence/ID per project or globally
        # For simplicity in this implementation, we'll use a timestamp-based approach
        # or track the last seen request_id globally if we assume unique IDs.
        self._last_processed_timestamp = None

    def add_callback(self, callback: Callable[[str, ExecutionResult], None]):
        """Registers a callback to be executed when a new success is detected.

        Args:
            callback: A callable that accepts (project_id, execution_result).
        """
        self._callbacks.append(callback)

    def start(self):
        """Starts the background observation thread."""
        if self._thread is not None:
            return

        # Initialize timestamp to now to avoid processing historic logs on start
        from datetime import datetime, timezone
        self._last_processed_timestamp = datetime.now(timezone.utc)

        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        logger.info("Audit log observer started.")

    def stop(self):
        """Stops the background observation thread."""
        self._stop_event.set()
        if self._thread:
            self._thread.join()
            self._thread = None
        logger.info("Audit log observer stopped.")

    def _run(self):
        """Main polling loop."""
        while not self._stop_event.is_set():
            try:
                self._poll_and_process()
            except Exception as e:
                logger.exception(f"Error in audit log observer poll: {str(e)}")
            
            self._stop_event.wait(self.poll_interval)

    def _poll_and_process(self):
        """Polls all projects for new successful executions."""
        projects = self.engine.repository.list_projects()
        
        for project in projects:
            project_id = project["id"]
            # Fetch recent history
            history = self.engine.repository.get_execution_history(
                project_id, limit=self.batch_size
            )
            
            # Reverse to process in chronological order
            new_entries = []
            for entry in reversed(history):
                # Filter for successes newer than our last check
                if entry.status == "success":
                    # Note: We compare timestamps. Accuracy depends on DB clock.
                    entry_ts = entry.timestamp
                    # Ensure timezone awareness for comparison if needed
                    if entry_ts.tzinfo is None:
                        from datetime import timezone
                        entry_ts = entry_ts.replace(tzinfo=timezone.utc)

                    if self._last_processed_timestamp is None or entry_ts > self._last_processed_timestamp:
                        new_entries.append(entry)

            # Process new entries
            for entry in new_entries:
                for cb in self._callbacks:
                    try:
                        cb(project_id, entry)
                    except Exception as e:
                        logger.error(f"Error in async observer callback: {str(e)}")
                
                # Update high watermark
                entry_ts = entry.timestamp
                if entry_ts.tzinfo is None:
                    from datetime import timezone
                    entry_ts = entry_ts.replace(tzinfo=timezone.utc)
                self._last_processed_timestamp = entry_ts
