"Example of Cross-Component Invariants.

This example demonstrates how to:
1. Define invariants that check constraints across multiple UI components.
2. Observe the engine blocking actions that violate system-wide safety rules."

from gradio_chat_agent.execution.engine import ExecutionEngine
from gradio_chat_agent.persistence.in_memory import InMemoryStateRepository
from gradio_chat_agent.registry.in_memory import InMemoryRegistry
from gradio_chat_agent.models.component import ComponentDeclaration, ComponentPermissions, ComponentInvariant
from gradio_chat_agent.models.action import ActionDeclaration, ActionPermission
from gradio_chat_agent.models.intent import ChatIntent
from gradio_chat_agent.models.enums import IntentType, ActionRisk, ActionVisibility
from gradio_chat_agent.models.state_snapshot import StateSnapshot

def run_example():
    registry = InMemoryRegistry()
    repository = InMemoryStateRepository()
    engine = ExecutionEngine(registry, repository)
    project_id = "cross-comp-safety"
    repository.create_project(project_id, "System Safety Demo")

    # 1. Register two related components
    # Logic: Total usage (CPU + GPU) cannot exceed 100%
    cpu_comp = ComponentDeclaration(
        component_id="sys.cpu",
        title="CPU Usage",
        description="CPU Load Percentage.",
        state_schema={"type": "object", "properties": {"load": {"type": "integer"}}},
        permissions=ComponentPermissions(readable=True),
        invariants=[
            ComponentInvariant(
                description="Total system load (CPU + GPU) must be <= 100%.",
                expr="state.get('sys.cpu', {}).get('load', 0) + state.get('sys.gpu', {}).get('load', 0) <= 100"
            )
        ]
    )
    gpu_comp = ComponentDeclaration(
        component_id="sys.gpu",
        title="GPU Usage",
        description="GPU Load Percentage.",
        state_schema={"type": "object", "properties": {"load": {"type": "integer"}}},
        permissions=ComponentPermissions(readable=True)
    )
    
    registry.register_component(cpu_cpu := cpu_comp) # Keep reference
    registry.register_component(gpu_gpu := gpu_comp)

    # 2. Register 'Set Load' action
    def set_load_handler(inputs, snapshot):
        target = inputs["component"]
        val = inputs["load"]
        new_comps = snapshot.components.copy()
        new_comps[target] = {"load": val}
        return new_comps, [], f"{target} set to {val}%"

    set_action = ActionDeclaration(
        action_id="sys.load.set",
        title="Set Load",
        description="Sets the load for a component.",
        targets=["sys.cpu", "sys.gpu"],
        input_schema={
            "type": "object",
            "properties": {
                "component": {"type": "string", "enum": ["sys.cpu", "sys.gpu"]},
                "load": {"type": "integer"}
            }
        },
        permission=ActionPermission(confirmation_required=False, risk=ActionRisk.LOW, visibility=ActionVisibility.USER)
    )
    registry.register_action(set_action, set_load_handler)

    # 3. Initial State (CPU=40, GPU=40, Total=80)
    repository.save_snapshot(project_id, StateSnapshot(snapshot_id="init", components={
        "sys.cpu": {"load": 40},
        "sys.gpu": {"load": 40}
    }))
    print("Initial State: CPU=40%, GPU=40% (Total=80%)")

    # 4. Valid Mutation (Set CPU to 50, Total=90)
    print("\n--- Scenario 1: Valid Mutation (Set CPU to 50%) ---")
    res1 = engine.execute_intent(project_id, ChatIntent(
        type=IntentType.ACTION_CALL, request_id="r1", 
        action_id="sys.load.set", inputs={"component": "sys.cpu", "load": 50}
    ))
    print(f"Status: {res1.status}, Message: {res1.message}")

    # 5. Invalid Mutation (Set GPU to 60, Total=50+60=110 > 100)
    print("\n--- Scenario 2: Violating Cross-Component Invariant (Set GPU to 60%) ---")
    res2 = engine.execute_intent(project_id, ChatIntent(
        type=IntentType.ACTION_CALL, request_id="r2", 
        action_id="sys.load.set", inputs={"component": "sys.gpu", "load": 60}
    ))
    print(f"Status: {res2.status}, Error: {res2.message}")

    # 6. Verify State (Should still be CPU=50, GPU=40)
    latest = repository.get_latest_snapshot(project_id)
    cpu = latest.components["sys.cpu"]["load"]
    gpu = latest.components["sys.gpu"]["load"]
    print(f"\nFinal State: CPU={cpu}%, GPU={gpu}% (Total={cpu+gpu}%)")

if __name__ == "__main__":
    run_example()
