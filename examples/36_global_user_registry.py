"""Example of Global User Registry Management via API.

This example demonstrates how to:
1. List all users in the system.
2. Delete a user.
"""

from gradio_chat_agent.api.endpoints import ApiEndpoints
from gradio_chat_agent.execution.engine import ExecutionEngine
from gradio_chat_agent.persistence.in_memory import InMemoryStateRepository
from gradio_chat_agent.registry.in_memory import InMemoryRegistry

def run_example():
    repo = InMemoryStateRepository()
    engine = ExecutionEngine(InMemoryRegistry(), repo)
    api = ApiEndpoints(engine)
    
    # 1. Create some users
    print("Creating users...")
    repo.create_user("user1", "hash", full_name="User One")
    repo.create_user("user2", "hash", full_name="User Two")
    
    # 2. List Users
    print("\n--- Listing Users ---")
    res = api.list_users()
    for u in res["data"]:
        print(f"ID: {u['id']}, Name: {u['full_name']}")
        
    # 3. Delete a user
    print("\nDeleting user1...")
    api.delete_user("user1")
    
    # 4. Verify
    print("\n--- Listing Users after deletion ---")
    res = api.list_users()
    for u in res["data"]:
        print(f"ID: {u['id']}, Name: {u['full_name']}")

if __name__ == "__main__":
    run_example()
