"""Example of Advanced Policy Rules.

This example demonstrates how to:
1. Define custom governance rules using Python expressions.
2. Block actions based on state (e.g., maintenance mode).
3. Require approval based on input values (e.g., large increments).
4. Restrict actions based on user roles and attributes.
"""

from gradio_chat_agent.execution.engine import ExecutionEngine
from gradio_chat_agent.persistence.in_memory import InMemoryStateRepository
from gradio_chat_agent.registry.in_memory import InMemoryRegistry
from gradio_chat_agent.models.action import ActionDeclaration, ActionPermission
from gradio_chat_agent.models.intent import ChatIntent
from gradio_chat_agent.models.enums import IntentType, ExecutionStatus, ActionRisk, ActionVisibility
from gradio_chat_agent.models.state_snapshot import StateSnapshot

def run_example():
    # 1. Setup system
    registry = InMemoryRegistry()
    repository = InMemoryStateRepository()
    engine = ExecutionEngine(registry, repository)
    project_id = "policy-demo"
    repository.create_project(project_id, "Advanced Policy Demo")

    # 2. Register Actions
    registry.register_action(
        ActionDeclaration(
            action_id="demo.counter.increment", title="Inc", description="Inc", targets=["t"], 
            input_schema={"type": "object", "properties": {"amount": {"type": "integer"}}},
            permission=ActionPermission(confirmation_required=False, risk=ActionRisk.LOW, visibility=ActionVisibility.USER)
        ),
        handler=lambda i, s: ({"counter": {"value": s.components.get("counter", {}).get("value", 0) + i.get("amount", 1)}}, [], "OK")
    )

    # 3. Define Advanced Policy Rules
    policy = {
        "rules": [
            {
                "id": "maintenance_mode",
                "description": "Block all actions if maintenance mode is ON in state.",
                "condition": "state.get('system.status', {}).get('maintenance') == True",
                "effect": "reject",
                "message": "System is currently under maintenance. Please try again later."
            },
            {
                "id": "large_increment_approval",
                "description": "Increments > 100 require approval.",
                "condition": "action_id == 'demo.counter.increment' and inputs.get('amount', 0) > 100",
                "effect": "require_approval",
                "message": "Increments larger than 100 units must be approved by an administrator."
            },
            {
                "id": "restrict_operator_high_val",
                "description": "Operators cannot set values > 1000.",
                "condition": "'operator' in roles and inputs.get('value', 0) > 1000",
                "effect": "reject",
                "message": "Operators are not allowed to set values exceeding 1000."
            }
        ]
    }
    repository.set_project_limits(project_id, policy)

    print("--- Scenario 1: Maintenance Mode ---")
    repository.save_snapshot(project_id, StateSnapshot(snapshot_id="s1", components={"system.status": {"maintenance": True}}))
    
    intent = ChatIntent(type=IntentType.ACTION_CALL, request_id="r1", action_id="demo.counter.increment", inputs={"amount": 1})
    res1 = engine.execute_intent(project_id, intent, user_roles=["admin"])
    print(f"Result (Maintenance ON): {res1.status} - {res1.message}")

    print("\n--- Scenario 2: Large Increment Approval ---")
    repository.save_snapshot(project_id, StateSnapshot(snapshot_id="s2", components={"system.status": {"maintenance": False}}))
    
    intent_large = ChatIntent(type=IntentType.ACTION_CALL, request_id="r2", action_id="demo.counter.increment", inputs={"amount": 500})
    res2 = engine.execute_intent(project_id, intent_large, user_roles=["operator"])
    print(f"Result (Amount 500): {res2.status} - {res2.message}")

    print("\n--- Scenario 3: Operator Restriction ---")
    registry.register_action(
        ActionDeclaration(
            action_id="demo.counter.set", title="Set", description="Set", targets=["t"], 
            input_schema={"type": "object", "properties": {"value": {"type": "integer"}}},
            permission=ActionPermission(confirmation_required=False, risk=ActionRisk.LOW, visibility=ActionVisibility.USER)
        ),
        handler=lambda i, s: ({}, [], "OK")
    )
    intent_set = ChatIntent(type=IntentType.ACTION_CALL, request_id="r3", action_id="demo.counter.set", inputs={"value": 5000})
    res3 = engine.execute_intent(project_id, intent_set, user_roles=["operator"])
    print(f"Result (Operator set 5000): {res3.status} - {res3.message}")

if __name__ == "__main__":
    run_example()
