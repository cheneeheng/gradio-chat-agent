"""Example of configuring a Scheduled Task.

This example demonstrates:
1. Registering an action and component.
2. Creating a schedule record in the repository.
3. How the SchedulerWorker detects and triggers the task.
"""

import time
from gradio_chat_agent.execution.engine import ExecutionEngine
from gradio_chat_agent.execution.scheduler import SchedulerWorker
from gradio_chat_agent.persistence.in_memory import InMemoryStateRepository
from gradio_chat_agent.registry.in_memory import InMemoryRegistry
from gradio_chat_agent.registry.demo_actions import counter_component, increment_action, increment_handler

def run_example():
    # 1. Setup system
    registry = InMemoryRegistry()
    repository = InMemoryStateRepository()
    engine = ExecutionEngine(registry, repository)
    
    registry.register_component(counter_component)
    registry.register_action(increment_action, increment_handler)
    
    project_id = "scheduler-demo"
    repository.create_project(project_id, "Scheduler Demo")
    
    # 2. Start Scheduler Worker (with fast polling for demo)
    worker = SchedulerWorker(engine, poll_interval=1)
    worker.start()
    
    try:
        print(f"--- Scenario: Schedule increment every minute ---")
        
        # 3. Add schedule record
        # Cron: Every minute
        repository.save_schedule({
            "id": "inc-every-min",
            "project_id": project_id,
            "action_id": "demo.counter.increment",
            "cron": "* * * * *",
            "inputs": {"amount": 10},
            "enabled": True
        })
        
        print("Schedule added. Waiting 2 seconds for worker to detect it...")
        time.sleep(2)
        
        # 4. Trigger the job manually for demonstration
        # (Instead of waiting a full minute)
        print("Manually triggering the scheduled job callback for demo...")
        job = worker.scheduler.get_job("inc-every-min")
        if job:
            job.func(*job.args)
        
        # 5. Verify state
        time.sleep(1)
        latest = repository.get_latest_snapshot(project_id)
        val = latest.components["demo.counter"]["value"] if latest else 0
        print(f"Counter Value: {val} (Expected: 10)")
        
    finally:
        worker.stop()

if __name__ == "__main__":
    run_example()
