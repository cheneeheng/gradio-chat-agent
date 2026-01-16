"""Example of Execution Windows and Hourly Rate Limiting.

This example demonstrates how to:
1. Configure time-of-day and day-of-week restrictions.
2. Set hourly rate limits to prevent runaway automation.
3. Observe the engine rejecting actions outside of allowed windows.
"""

import uuid
from datetime import datetime, timezone
from gradio_chat_agent.execution.engine import ExecutionEngine
from gradio_chat_agent.models.action import (
    ActionDeclaration,
    ActionPermission,
)
from gradio_chat_agent.models.enums import (
    ActionRisk,
    ActionVisibility,
    IntentType,
)
from gradio_chat_agent.models.intent import ChatIntent
from gradio_chat_agent.persistence.in_memory import InMemoryStateRepository
from gradio_chat_agent.registry.in_memory import InMemoryRegistry

def run_example():
    registry = InMemoryRegistry()
    repository = InMemoryStateRepository()
    engine = ExecutionEngine(registry, repository)
    project_id = "governance-demo"
    repository.create_project(project_id, "Governance Demo")

    # Register a simple action
    action = ActionDeclaration(
        action_id="demo.action",
        title="Test Action",
        description="A simple action.",
        targets=["demo"],
        input_schema={},
        permission=ActionPermission(
            confirmation_required=False,
            risk=ActionRisk.LOW,
            visibility=ActionVisibility.USER,
        )
    )
    registry.register_action(action, lambda i, s: ({}, [], "Done"))

    # 1. Setup Execution Windows
    # Allow only on weekdays during standard business hours (8 AM - 6 PM UTC)
    print("--- Phase 1: Execution Windows ---")
    policy = {
        "execution_windows": {
            "allowed": [
                {
                    "days": ["mon", "tue", "wed", "thu", "fri"],
                    "hours": ["08:00", "18:00"]
                }
            ]
        },
        "limits": {
            "rate": {
                "per_hour": 100
            }
        }
    }
    repository.set_project_limits(project_id, policy)

    intent = ChatIntent(
        type=IntentType.ACTION_CALL,
        request_id=str(uuid.uuid4()),
        action_id="demo.action",
        inputs={}
    )

    # We can't easily control the system clock in this example, but we can see the logic.
    res = engine.execute_intent(project_id, intent)
    
    now = datetime.now(timezone.utc)
    is_weekday = now.strftime("%a").lower() in ["mon", "tue", "wed", "thu", "fri"]
    is_business_hours = "08:00" <= now.strftime("%H:%M") <= "18:00"
    
    if is_weekday and is_business_hours:
        print(f"Result (Currently within window): {res.status}")
    else:
        print(f"Result (Currently outside window): {res.status} (Code: {res.error.code if res.error else 'None'})")

    # 2. Setup Hourly Rate Limiting
    print("\n--- Phase 2: Hourly Rate Limiting ---")
    # Set limit to 2 per hour
    policy["limits"]["rate"]["per_hour"] = 2
    repository.set_project_limits(project_id, policy)

    # First two should succeed (assuming we are in the window)
    for i in range(3):
        intent = ChatIntent(
            type=IntentType.ACTION_CALL,
            request_id=f"req-{i}",
            action_id="demo.action",
            inputs={}
        )
        res = engine.execute_intent(project_id, intent)
        
        # If blocked by window, skip this part of the demo
        if res.status == "rejected" and res.error.code == "execution_window_violation":
            print("Skipping rate limit check: Currently outside allowed execution window.")
            break
            
        print(f"Attempt {i+1}: {res.status} {f'(Error: {res.error.code})' if res.error else ''}")

if __name__ == "__main__":
    run_example()
