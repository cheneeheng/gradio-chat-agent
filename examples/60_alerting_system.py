"""Example of the Operational Alerting System.

This example demonstrates how:
1. The AlertingService monitors execution results.
2. Alerts are triggered for high failure rates, high latency, and budget usage.
3. Custom handlers can be added to receive alerts.
"""

import time
from unittest.mock import MagicMock
from gradio_chat_agent.execution.engine import ExecutionEngine
from gradio_chat_agent.observability.alerting import AlertingService
from gradio_chat_agent.persistence.in_memory import InMemoryStateRepository
from gradio_chat_agent.registry.in_memory import InMemoryRegistry
from gradio_chat_agent.models.intent import ChatIntent
from gradio_chat_agent.models.enums import IntentType, ExecutionStatus

def run_example():
    # 1. Setup system
    repo = InMemoryStateRepository()
    registry = InMemoryRegistry()
    engine = ExecutionEngine(registry, repo)
    alert_service = AlertingService(engine)
    
    project_id = "alert-demo"
    repo.create_project(project_id, "Alert Demo")
    
    # 2. Add a custom handler to track alerts in this example
    captured_alerts = []
    def my_handler(alert):
        print(f"Captured Alert: {alert['type']} - {alert['message']}")
        captured_alerts.append(alert)
    
    alert_service.add_handler(my_handler)
    
    # 3. Simulate Budget Exhaustion (Threshold 80%)
    print("--- Scenario 1: Budget Exhaustion ---")
    repo.set_project_limits(project_id, {"limits": {"budget": {"daily": 100.0}}})
    
    # Mock an expensive action result
    # We need to use engine.execute_intent to trigger the hook, or call alert_service directly
    # For the example, I'll call it via engine to show integration
    
    # Setup dummy action
    from gradio_chat_agent.models.action import ActionDeclaration, ActionPermission
    registry.register_action(
        ActionDeclaration(
            action_id="expensive", title="E", description="E", targets=["t"], 
            input_schema={}, cost=85.0,
            permission=ActionPermission(confirmation_required=False, risk="low", visibility="user")
        ),
        handler=lambda i, s: ({}, [], "Done")
    )
    # Register the service hook
    engine.add_post_execution_hook(alert_service.check_execution_alerts)
    
    intent = ChatIntent(type=IntentType.ACTION_CALL, request_id="r1", action_id="expensive")
    engine.execute_intent(project_id, intent, user_roles=["admin"])
    
    # 4. Simulate High Latency
    print("\n--- Scenario 2: High Latency ---")
    # Mock a result with high latency
    slow_res = MagicMock(
        action_id="slow_act",
        execution_time_ms=15000, # 15s
        status=ExecutionStatus.SUCCESS,
        simulated=False
    )
    alert_service.check_execution_alerts(project_id, slow_res)
    
    # 5. Simulate High Failure Rate
    print("\n--- Scenario 3: High Failure Rate ---")
    # Add 9 failures and 1 success in the last 5 minutes
    from datetime import datetime, timezone
    for i in range(9):
        fail_res = ExecutionResult(
            request_id=f"f{i}",
            action_id="act",
            status=ExecutionStatus.FAILED,
            timestamp=datetime.now(timezone.utc),
            state_snapshot_id="err",
            metadata={}
        )
        repo.save_execution(project_id, fail_res)
    
    # 10th execution (must exceed 10 for check)
    last_res = ExecutionResult(
        request_id="r10",
        action_id="act",
        status=ExecutionStatus.SUCCESS,
        timestamp=datetime.now(timezone.utc),
        state_snapshot_id="ok",
        execution_time_ms=100,
        simulated=False
    )
    alert_service.check_execution_alerts(project_id, last_res)

    print(f"\nTotal alerts captured: {len(captured_alerts)}")

if __name__ == "__main__":
    run_example()
