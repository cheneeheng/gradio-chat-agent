"""Example showing Task Retry logic in the Scheduler.

This example simulates a failing action and demonstrates 
how the SchedulerWorker retries it.
"""

import time
from unittest.mock import MagicMock
from gradio_chat_agent.execution.engine import ExecutionEngine
from gradio_chat_agent.execution.scheduler import SchedulerWorker
from gradio_chat_agent.persistence.in_memory import InMemoryStateRepository
from gradio_chat_agent.registry.in_memory import InMemoryRegistry

def run_example():
    repo = InMemoryStateRepository()
    engine = ExecutionEngine(InMemoryRegistry(), repo)
    
    # Mock engine.execute_intent to fail then succeed? 
    # Or just log the attempts.
    original_execute = engine.execute_intent
    
    attempts = 0
    def mock_execute(*args, **kwargs):
        nonlocal attempts
        attempts += 1
        print(f"Engine execute_intent called. Attempt: {attempts}")
        # Fail the first 2 times, then succeed? 
        # Actually, SchedulerWorker logic just checks for 'success' status.
        return MagicMock(status="failed", message="Simulated Failure")

    engine.execute_intent = mock_execute
    
    worker = SchedulerWorker(engine)
    
    print("Triggering scheduled action with retries...")
    worker._execute_scheduled_action({
        "id": "s1",
        "project_id": "p1",
        "action_id": "demo.act",
        "inputs": {}
    })
    
    print(f"\nTotal attempts made by worker: {attempts}")
    assert attempts == 3

if __name__ == "__main__":
    run_example()

