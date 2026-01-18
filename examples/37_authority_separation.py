"Example of Authority Separation (System Admin vs Project Admin).

This example demonstrates how:
1. Only 'admin' user (System Admin) can create new projects.
2. Other users (even Project Admins) are rejected from platform management.
"

from gradio_chat_agent.api.endpoints import ApiEndpoints
from gradio_chat_agent.execution.engine import ExecutionEngine
from gradio_chat_agent.persistence.in_memory import InMemoryStateRepository
from gradio_chat_agent.registry.in_memory import InMemoryRegistry
from gradio_chat_agent.models.enums import ProjectOp

def run_example():
    api = ApiEndpoints(ExecutionEngine(InMemoryRegistry(), InMemoryStateRepository()))
    
    print("--- Scenario 1: Non-Admin attempts project creation ---")
    res1 = api.manage_project(ProjectOp.CREATE, name="Shadow Project", user_id="alice")
    print(f"User: alice, Result: {res1['message']} (Code: {res1['code']})")
    
    print("\n--- Scenario 2: System Admin ('admin') creates project ---")
    res2 = api.manage_project(ProjectOp.CREATE, name="Official Project", user_id="admin")
    print(f"User: admin, Result: {res2['message']}, Project ID: {res2['data']['project_id']}")

if __name__ == "__main__":
    run_example()

