"""Example of using the Org Rollup API.

This example demonstrates how a System Admin can retrieve aggregated
statistics across all projects in the platform.
"""

import json
from gradio_chat_agent.api.endpoints import ApiEndpoints
from gradio_chat_agent.execution.engine import ExecutionEngine
from gradio_chat_agent.persistence.in_memory import InMemoryStateRepository
from gradio_chat_agent.registry.in_memory import InMemoryRegistry
from gradio_chat_agent.models.intent import ChatIntent
from gradio_chat_agent.models.enums import IntentType

def run_example():
    # 1. Setup system with some data
    repo = InMemoryStateRepository()
    engine = ExecutionEngine(InMemoryRegistry(), repo)
    api = ApiEndpoints(engine)
    
    # Create two projects
    api.manage_project(op="create", name="Project A", project_id="proj-a", user_id="admin")
    api.manage_project(op="create", name="Project B", project_id="proj-b", user_id="admin")
    
    # Register a dummy action with cost
    from gradio_chat_agent.models.action import ActionDeclaration, ActionPermission
    action = ActionDeclaration(
        action_id="dummy.act", title="D", description="D", targets=["t"], 
        input_schema={}, cost=15.0,
        permission=ActionPermission(confirmation_required=False, risk="low", visibility="user")
    )
    engine.registry.register_action(action, lambda i, s: ({}, [], "ok"))
    
    # Execute some actions in Project A
    for i in range(3):
        engine.execute_intent("proj-a", ChatIntent(type=IntentType.ACTION_CALL, request_id=f"a-{i}", action_id="dummy.act"), user_roles=["admin"])
        
    # Execute one action in Project B
    engine.execute_intent("proj-b", ChatIntent(type=IntentType.ACTION_CALL, request_id="b-1", action_id="dummy.act"), user_roles=["admin"])

    # 2. Retrieve Org Rollup (as System Admin)
    print("--- Retrieving Org Rollup ---")
    response = api.api_org_rollup(user_id="admin")
    
    if response["code"] == 0:
        data = response["data"]
        print(f"Total Projects: {data['total_projects']}")
        print(f"Total Executions: {data['total_executions']}")
        print(f"Total Platform Cost: {data['total_cost']}")
        
        print("\nPer-Project Breakdown:")
        for pid, stats in data["projects"].items():
            print(f"  - {stats['project_name']} ({pid}): {stats['success_count']} successes, Cost: {stats['total_cost']}")
    else:
        print(f"Error: {response['message']}")

    # 3. Unauthorized access attempt
    print("\n--- Testing Unauthorized Access ---")
    anon_response = api.api_org_rollup(user_id="alice")
    print(f"User 'alice' response: {anon_response['message']} (Code: {anon_response['code']})")

if __name__ == "__main__":
    run_example()
