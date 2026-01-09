"""Example of governance and role enforcement in the execution engine.

This example demonstrates:
1. Rejection of high-risk actions for low-privileged users.
2. Enforcement of confirmation gates.
3. Precondition checking preventing invalid transitions.
"""

from gradio_chat_agent.execution.engine import ExecutionEngine
from gradio_chat_agent.models.action import (
    ActionDeclaration,
    ActionPermission,
    ActionPrecondition,
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
    project_id = "governance-demo"

    # Setup initial state
    repository.save_snapshot(
        project_id,
        StateSnapshot(
            snapshot_id="init",
            components={"system.power": {"status": "off"}},
        ),
    )

    # 1. Register a HIGH RISK action that requires ADMIN and CONFIRMATION
    nuke_action = ActionDeclaration(
        action_id="system.reset.all",
        title="Factory Reset",
        description="DESTRUCTIVE: Resets the entire system.",
        targets=["system.power"],
        input_schema={},
        permission=ActionPermission(
            confirmation_required=True,
            risk=ActionRisk.HIGH,
            visibility=ActionVisibility.USER,
        ),
    )
    registry.register_action(
        nuke_action, lambda i, s: ({}, [], "System Wiped")
    )

    # 2. Register an action with a PRECONDITION
    # Can only turn power 'on' if it is currently 'off'
    power_on_action = ActionDeclaration(
        action_id="system.power.on",
        title="Power On",
        description="Turns on the system.",
        targets=["system.power"],
        input_schema={},
        preconditions=[
            ActionPrecondition(
                id="check.is.off",
                description="System must be off.",
                expr="state['system.power']['status'] == 'off'",
            )
        ],
        permission=ActionPermission(
            confirmation_required=False,
            risk=ActionRisk.LOW,
            visibility=ActionVisibility.USER,
        ),
    )
    registry.register_action(
        power_on_action,
        lambda i, s: ({"system.power": {"status": "on"}}, [], "Power is ON"),
    )

    print("--- Scenario 1: Insufficient Roles ---")
    intent_nuke = ChatIntent(
        type=IntentType.ACTION_CALL,
        request_id="r1",
        action_id="system.reset.all",
        inputs={},
    )
    res = engine.execute_intent(
        project_id, intent_nuke, user_roles=["operator"]
    )
    print(f"Result (Operator): {res.status} - {res.message}")

    print("\n--- Scenario 2: Missing Confirmation ---")
    res = engine.execute_intent(project_id, intent_nuke, user_roles=["admin"])
    print(f"Result (Admin, no confirm): {res.status} - {res.message}")

    print("\n--- Scenario 3: Precondition Failure ---")
    # First turn it on
    intent_on = ChatIntent(
        type=IntentType.ACTION_CALL,
        request_id="r2",
        action_id="system.power.on",
        inputs={},
    )
    engine.execute_intent(project_id, intent_on)

    # Try to turn it on again
    res = engine.execute_intent(project_id, intent_on)
    print(f"Result (Power on while already on): {res.status} - {res.message}")

    print("\n--- Scenario 4: Successful High-Risk Action ---")
    intent_nuke.confirmed = True
    res = engine.execute_intent(project_id, intent_nuke, user_roles=["admin"])
    print(f"Result (Admin, confirmed): {res.status} - {res.message}")


if __name__ == "__main__":
    run_example()
