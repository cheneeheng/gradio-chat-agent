"""Example of using the Huey Worker Pool for background tasks.

This example demonstrates how to:
1. Enqueue an action for background execution.
2. How the worker (simulated) would process it.
"""

import os
import time
from gradio_chat_agent.execution.tasks import execute_background_action, huey

def run_example():
    print("--- Phase 1: Background Task Enqueuing ---")
    
    # Simulate enqueuing a task
    # In a real app, this happens in ApiEndpoints or SchedulerWorker
    project_id = "default_project"
    action_id = "demo.counter.increment"
    inputs = {"amount": 5}
    
    print(f"Enqueuing action {action_id} for project {project_id}...")
    result = execute_background_action(project_id, action_id, inputs, "example_user", "manual_trigger")
    
    print(f"Task enqueued! Huey Task ID: {result.id}")

    print("\n--- Phase 2: Simulated Worker Execution ---")
    # In a real scenario, you'd run 'gradio-agent worker start'
    # Here we'll manually trigger the task processing if we had a worker running.
    # Since Huey SqliteHuey is persistent, the task is now in 'huey_queue.db'.
    
    print("To process this task, run:")
    print("uv run gradio-agent worker start")
    
    # We can also check pending tasks in huey
    pending = huey.pending()
    print(f"Pending tasks in queue: {len(pending)}")

    print("\nExample complete.")

if __name__ == "__main__":
    run_example()
