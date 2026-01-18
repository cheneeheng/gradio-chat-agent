"""Example of Budget Forecasting Service.

This example demonstrates how:
1. The ForecastingService calculates burn rate.
2. It predicts when a project will run out of budget for the day.
"""

from gradio_chat_agent.api.endpoints import ApiEndpoints
from gradio_chat_agent.execution.engine import ExecutionEngine
from gradio_chat_agent.persistence.in_memory import InMemoryStateRepository
from gradio_chat_agent.registry.in_memory import InMemoryRegistry
from gradio_chat_agent.models.intent import ChatIntent
from gradio_chat_agent.models.enums import IntentType

def run_example():
    repo = InMemoryStateRepository()
    engine = ExecutionEngine(InMemoryRegistry(), repo)
    api = ApiEndpoints(engine)
    
    project_id = "forecast-demo"
    repo.create_project(project_id, "Forecast Demo")
    
    # 1. No Limit Case
    print("--- Scenario 1: No Budget Limit ---")
    print(api.budget_forecast(project_id)["data"]["message"])
    
    # 2. Set Limit
    repo.set_project_limits(project_id, {"limits": {"budget": {"daily": 100.0}}})
    
    # 3. Simulate usage
    # We need some historical entries today to calculate a burn rate > 0
    print("\n--- Scenario 2: With usage ---")
    # Manually register an action with cost 10
    from gradio_chat_agent.models.action import ActionDeclaration, ActionPermission
    action = ActionDeclaration(
        action_id="expensive.act", title="E", description="E", targets=["t"], 
        input_schema={}, cost=10.0,
        permission=ActionPermission(confirmation_required=False, risk="low", visibility="user")
    )
    engine.registry.register_action(action, lambda i, s: ({}, [], "ok"))
    
    # Execute a few times
    for i in range(5):
        engine.execute_intent(project_id, ChatIntent(type=IntentType.ACTION_CALL, request_id=f"r{i}", action_id="expensive.act"), user_roles=["admin"])
        
    forecast = api.budget_forecast(project_id)["data"]
    print(f"Status: {forecast['status']}")
    print(f"Usage: {forecast['current_usage']}/{forecast['daily_limit']}")
    print(f"Burn Rate: {forecast['burn_rate_per_hour']:.2f} units/hour")
    print(f"Estimated Exhaustion: {forecast['estimated_exhaustion_at']}")

if __name__ == "__main__":
    run_example()
