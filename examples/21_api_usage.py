"""Example of using the Headless API with Standardized Responses and Simulation.

This example demonstrates:
1. Executing an action via the API and handling the ApiResponse envelope.
2. Simulating an action to preview its impact.
3. Executing and simulating multi-step plans.
"""

import uuid
from gradio_chat_agent.execution.engine import ExecutionEngine
from gradio_chat_agent.api.endpoints import ApiEndpoints
from gradio_chat_agent.persistence.in_memory import InMemoryStateRepository
from gradio_chat_agent.registry.in_memory import InMemoryRegistry
from gradio_chat_agent.registry.demo_actions import (
    counter_component,
    set_action,
    set_handler,
    increment_action,
    increment_handler
)

def run_example():
    # 1. Setup
    registry = InMemoryRegistry()
    repository = InMemoryStateRepository()
    engine = ExecutionEngine(registry, repository)
    api = ApiEndpoints(engine)
    
    project_id = "api-demo-project"
    repository.create_project(project_id, "API Demo")
    
    registry.register_component(counter_component)
    registry.register_action(set_action, set_handler)
    registry.register_action(increment_action, increment_handler)

    print("--- Scenario 1: Execute Action ---")
    response = api.execute_action(
        project_id=project_id,
        action_id="demo.counter.set",
        inputs={"value": 10}
    )
    print(f"API Code: {response['code']}")
    print(f"API Message: {response['message']}")
    print(f"Data Status: {response['data']['status']}")
    print(f"New Value: {repository.get_latest_snapshot(project_id).components['demo.counter']['value']}")

    print("\n--- Scenario 2: Simulate Action ---")
    sim_response = api.simulate_action(
        project_id=project_id,
        action_id="demo.counter.set",
        inputs={"value": 100}
    )
    print(f"API Code: {sim_response['code']}")
    print(f"Simulated: {sim_response['data']['simulated']}")
    print(f"Proposed Diff: {sim_response['data']['state_diff']}")
    # Verify state didn't change
    print(f"Actual Value (unchanged): {repository.get_latest_snapshot(project_id).components['demo.counter']['value']}")

    print("\n--- Scenario 3: Simulate Plan ---")
    plan = {
        "plan_id": "p-1",
        "steps": [
            {
                "type": "action_call",
                "request_id": "s-1",
                "action_id": "demo.counter.set",
                "inputs": {"value": 50},
                "timestamp": "2023-01-01T00:00:00Z"
            },
            {
                "type": "action_call",
                "request_id": "s-2",
                "action_id": "demo.counter.increment",
                "inputs": {"amount": 25},
                "timestamp": "2023-01-01T00:00:00Z"
            }
        ]
    }
    plan_sim_res = api.simulate_plan(project_id, plan)
    print(f"Plan API Code: {plan_sim_res['code']}")
    for i, step_res in enumerate(plan_sim_res['data']):
        print(f"Step {i+1} ({step_res['action_id']}) Simulated: {step_res['simulated']}")

    # Verify state still 10
    print(f"Actual Value (still 10): {repository.get_latest_snapshot(project_id).components['demo.counter']['value']}")

if __name__ == "__main__":
    run_example()
