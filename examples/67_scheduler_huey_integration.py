"""Example of Scheduler integration with Huey Worker Pool.

This example demonstrates how to:
1. Initialize the SchedulerWorker with use_huey=True.
2. Configure a scheduled task.
3. Observe how the scheduler enqueues the task into Huey.
"""

import time
import os
from gradio_chat_agent.execution.engine import ExecutionEngine
from gradio_chat_agent.execution.scheduler import SchedulerWorker
from gradio_chat_agent.persistence.in_memory import InMemoryStateRepository
from gradio_chat_agent.registry.in_memory import InMemoryRegistry
from gradio_chat_agent.registry.demo_actions import counter_component, increment_action, increment_handler
from gradio_chat_agent.execution.tasks import huey

def run_example():
    # 1. Setup system
    registry = InMemoryRegistry()
    repository = InMemoryStateRepository()
    engine = ExecutionEngine(registry, repository)
    
    registry.register_component(counter_component)
    registry.register_action(increment_action, increment_handler)
    
    project_id = "huey-scheduler-demo"
    repository.create_project(project_id, "Huey Scheduler Demo")
    
    # 2. Start Scheduler Worker with Huey enabled
    # poll_interval set to 1 for fast detection in demo
    worker = SchedulerWorker(engine, poll_interval=1, use_huey=True)
    worker.start()
    
    try:
        print(f"--- Scenario: Schedule task with Huey offloading ---")
        
        # 3. Add schedule record
        repository.save_schedule({
            "id": "huey-task-1",
            "project_id": project_id,
            "action_id": "demo.counter.increment",
            "cron": "* * * * *",
            "inputs": {"amount": 50},
            "enabled": True
        })
        
        print("Schedule added. Waiting for worker to detect and sync...")
        time.sleep(2)
        
        # 4. Manually trigger the scheduled job callback
        # This simulates the cron trigger firing
        print("Triggering the scheduled job...")
        job = worker.scheduler.get_job("huey-task-1")
        if job:
            # This call should ENQUEUE a task in Huey, not execute it
            job.func(*job.args)
        
        # 5. Verify Huey Queue
        pending = huey.pending()
        print(f"Tasks pending in Huey queue: {len(pending)}")
        for t in pending:
            print(f"  - Task ID: {t.id}, Name: {t.name}")
            
        if len(pending) > 0:
            print("\nSUCCESS: Scheduler successfully offloaded task to Huey.")
        else:
            print("\nFAILURE: No tasks found in Huey queue.")

        print("\nTo process these tasks, you would run:")
        print("uv run gradio-agent worker start")

    finally:
        worker.stop()

if __name__ == "__main__":
    run_example()
