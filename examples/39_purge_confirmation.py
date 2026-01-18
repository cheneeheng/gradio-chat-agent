"""Example of Purge Confirmation Gate.

This example demonstrates how:
1. Attempting to PURGE a project without confirmation is rejected.
2. Successful PURGE requires confirmed=True.
"""

from gradio_chat_agent.api.endpoints import ApiEndpoints
from gradio_chat_agent.execution.engine import ExecutionEngine
from gradio_chat_agent.persistence.in_memory import InMemoryStateRepository
from gradio_chat_agent.registry.in_memory import InMemoryRegistry
from gradio_chat_agent.models.enums import ProjectOp

def run_example():
    repo = InMemoryStateRepository()
    api = ApiEndpoints(ExecutionEngine(InMemoryRegistry(), repo))
    
    repo.create_project("target-proj", "Target")
    
    print("--- Scenario 1: Purge without confirmation ---")
    res1 = api.manage_project(ProjectOp.PURGE, project_id="target-proj", user_id="admin", confirmed=False)
    print(f"Result: {res1['message']} (Code: {res1['code']})")
    
    print("\n--- Scenario 2: Purge WITH confirmation ---")
    res2 = api.manage_project(ProjectOp.PURGE, project_id="target-proj", user_id="admin", confirmed=True)
    print(f"Result: {res2['message']} (Code: {res2['code']})")
    
    # Verify
    projects = repo.list_projects()
    exists = any(p['id'] == "target-proj" for p in projects)
    print(f"\nProject exists after confirmed purge? {exists}")

if __name__ == "__main__":
    run_example()
