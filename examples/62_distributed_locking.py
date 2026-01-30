"""Example of Distributed Locking.

This example demonstrates how to:
1. Use the distributed lock to serialize access to a project.
2. Observe how concurrent attempts to acquire the lock are handled.
"""

import threading
import time
from gradio_chat_agent.execution.engine import ExecutionEngine
from gradio_chat_agent.persistence.in_memory import InMemoryStateRepository
from gradio_chat_agent.registry.in_memory import InMemoryRegistry

def run_example():
    # 1. Setup system
    registry = InMemoryRegistry()
    repository = InMemoryStateRepository()
    engine = ExecutionEngine(registry, repository)
    project_id = "locking-demo"

    def worker(worker_id, duration):
        print(f"Worker {worker_id}: Attempting to acquire lock...")
        try:
            with engine.project_lock(project_id, timeout=5):
                print(f"Worker {worker_id}: Lock acquired! Working for {duration}s...")
                time.sleep(duration)
                print(f"Worker {worker_id}: Work complete. Releasing lock.")
        except RuntimeError as e:
            print(f"Worker {worker_id}: Failed to acquire lock: {e}")

    # 2. Simulate concurrent access
    print(f"--- Starting Concurrent Workers for Project: {project_id} ---")
    
    t1 = threading.Thread(target=worker, args=(1, 2))
    t2 = threading.Thread(target=worker, args=(2, 1))
    
    t1.start()
    time.sleep(0.5) # Ensure t1 gets it first
    t2.start()
    
    t1.join()
    t2.join()

    print("\n--- Testing Lock Timeout ---")
    # This worker will hold the lock for longer than the timeout of the next worker
    t3 = threading.Thread(target=worker, args=(3, 4))
    t4 = threading.Thread(target=worker, args=(4, 1))
    
    t3.start()
    time.sleep(0.5)
    t4.start()
    
    t3.join()
    t4.join()

if __name__ == "__main__":
    run_example()
