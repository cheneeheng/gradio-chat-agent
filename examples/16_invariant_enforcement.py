"""Example of Component Invariants and Safety Enforcement.

This example demonstrates how to:
1. Define machine-readable invariants for UI components.
2. Observe the engine blocking actions that would lead to an invalid state.
3. Verify that state is preserved (rolled back) when an invariant is violated.
"""

import uuid
from typing import Any
from gradio_chat_agent.execution.engine import ExecutionEngine
from gradio_chat_agent.models.action import (
    ActionDeclaration,
    ActionPermission,
)
from gradio_chat_agent.models.component import (
    ComponentDeclaration,
    ComponentPermissions,
    ComponentInvariant,
)
from gradio_chat_agent.models.enums import (
    ActionRisk,
    ActionVisibility,
    IntentType,
)
from gradio_chat_agent.models.intent import ChatIntent
from gradio_chat_agent.models.state_snapshot import StateSnapshot
from gradio_chat_agent.persistence.in_memory import InMemoryStateRepository
from gradio_chat_agent.registry.in_memory import InMemoryRegistry

def run_example():
    registry = InMemoryRegistry()
    repository = InMemoryStateRepository()
    engine = ExecutionEngine(registry, repository)
    project_id = "safety-demo"
    repository.create_project(project_id, "Safety Demo")

    # 1. Register a component with an INVARIANT
    # The counter must always be between 0 and 100
    counter_comp = ComponentDeclaration(
        component_id="demo.bounded.counter",
        title="Bounded Counter",
        description="A counter that must stay within [0, 100].",
        state_schema={"type": "object", "properties": {"value": {"type": "integer"}}},
        permissions=ComponentPermissions(readable=True),
        invariants=[
            ComponentInvariant(
                description="Value cannot be negative.",
                expr="state['demo.bounded.counter']['value'] >= 0"
            ),
            ComponentInvariant(
                description="Value cannot exceed 100.",
                expr="state['demo.bounded.counter']['value'] <= 100"
            )
        ]
    )
    registry.register_component(counter_comp)

    # 2. Register a 'Set' action
    def set_handler(inputs: dict[str, Any], snapshot: StateSnapshot):
        new_val = inputs["value"]
        new_comps = snapshot.components.copy()
        new_comps["demo.bounded.counter"] = {"value": new_val}
        return new_comps, [], f"Set to {new_val}"

    set_action = ActionDeclaration(
        action_id="demo.counter.set",
        title="Set Value",
        description="Sets the counter value.",
        targets=["demo.bounded.counter"],
        input_schema={"type": "object", "properties": {"value": {"type": "integer"}}},
        permission=ActionPermission(confirmation_required=False, risk=ActionRisk.LOW, visibility=ActionVisibility.USER)
    )
    registry.register_action(set_action, set_handler)

    # Initialize state
    repository.save_snapshot(project_id, StateSnapshot(snapshot_id="init", components={"demo.bounded.counter": {"value": 50}}))
    print("Initial State: 50")

    # 3. Test valid mutation
    print("\n--- Scenario 1: Valid Mutation (Set to 75) ---")
    intent1 = ChatIntent(type=IntentType.ACTION_CALL, request_id="r1", action_id="demo.counter.set", inputs={"value": 75})
    res1 = engine.execute_intent(project_id, intent1)
    print(f"Status: {res1.status}, Message: {res1.message}")

    # 4. Test invalid mutation (too high)
    print("\n--- Scenario 2: Violating Upper Bound (Set to 150) ---")
    intent2 = ChatIntent(type=IntentType.ACTION_CALL, request_id="r2", action_id="demo.counter.set", inputs={"value": 150})
    res2 = engine.execute_intent(project_id, intent2)
    print(f"Status: {res2.status}, Error: {res2.message}")

    # 5. Test invalid mutation (negative)
    print("\n--- Scenario 3: Violating Lower Bound (Set to -10) ---")
    intent3 = ChatIntent(type=IntentType.ACTION_CALL, request_id="r3", action_id="demo.counter.set", inputs={"value": -10})
    res3 = engine.execute_intent(project_id, intent3)
    print(f"Status: {res3.status}, Error: {res3.message}")

    # 6. Verify final state (should still be 75)
    final_snap = repository.get_latest_snapshot(project_id)
    val = final_snap.components["demo.bounded.counter"]["value"]
    print(f"\nFinal State Value: {val} (Expected: 75)")

if __name__ == "__main__":
    run_example()
