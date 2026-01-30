"""Example of Component and Action Versioning in the Registry.

This example demonstrates how the Registry supports multiple versions of
components and actions using the '@vN' suffix, and how requesting an ID
without a version automatically resolves to the latest version.
"""

from typing import Any
from gradio_chat_agent.models.action import ActionDeclaration, ActionPermission
from gradio_chat_agent.models.component import ComponentDeclaration, ComponentPermissions
from gradio_chat_agent.models.enums import ActionRisk, ActionVisibility
from gradio_chat_agent.models.state_snapshot import StateSnapshot
from gradio_chat_agent.registry.in_memory import InMemoryRegistry


def run_example():
    registry = InMemoryRegistry()

    # 1. Register v1 of a component and action
    print("Registering v1 components and actions...")
    comp_v1 = ComponentDeclaration(
        component_id="demo.counter@v1",
        title="Counter V1",
        description="Version 1 of the counter.",
        state_schema={"type": "object", "properties": {"val": {"type": "integer"}}},
        permissions=ComponentPermissions(readable=True),
    )
    registry.register_component(comp_v1)

    action_v1 = ActionDeclaration(
        action_id="demo.counter.set@v1",
        title="Set V1",
        description="Set version 1.",
        targets=["demo.counter@v1"],
        input_schema={"type": "object", "properties": {"val": {"type": "integer"}}},
        permission=ActionPermission(confirmation_required=False, risk=ActionRisk.LOW, visibility=ActionVisibility.USER),
    )
    registry.register_action(action_v1, lambda i, s: ({}, [], "v1 done"))

    # 2. Register v2 of the same component and action
    print("Registering v2 components and actions...")
    comp_v2 = ComponentDeclaration(
        component_id="demo.counter@v2",
        title="Counter V2",
        description="Version 2 of the counter with more features.",
        state_schema={"type": "object", "properties": {"val": {"type": "integer"}, "label": {"type": "string"}}},
        permissions=ComponentPermissions(readable=True),
    )
    registry.register_component(comp_v2)

    action_v2 = ActionDeclaration(
        action_id="demo.counter.set@v2",
        title="Set V2",
        description="Set version 2.",
        targets=["demo.counter@v2"],
        input_schema={"type": "object", "properties": {"val": {"type": "integer"}}},
        permission=ActionPermission(confirmation_required=False, risk=ActionRisk.LOW, visibility=ActionVisibility.USER),
    )
    registry.register_action(action_v2, lambda i, s: ({}, [], "v2 done"))

    print("\n--- Testing Version Resolution ---")

    # 3. Explicit version request
    print(f"Requesting 'demo.counter@v1': {registry.get_component('demo.counter@v1').title}")
    print(f"Requesting 'demo.counter@v2': {registry.get_component('demo.counter@v2').title}")

    # 4. Implicit 'latest' version request
    latest_comp = registry.get_component("demo.counter")
    print(f"Requesting 'demo.counter' (implicit latest): {latest_comp.title} (ID: {latest_comp.component_id})")
    
    latest_action = registry.get_action("demo.counter.set")
    print(f"Requesting 'demo.counter.set' (implicit latest): {latest_action.title} (ID: {latest_action.action_id})")

    # 5. Handler resolution
    handler = registry.get_handler("demo.counter.set")
    _, _, msg = handler({}, StateSnapshot(snapshot_id="test", components={}))
    print(f"Executing handler for 'demo.counter.set' (implicit latest): {msg}")

    # 6. Verify sort order (v10 > v2)
    print("\nRegistering v10 to test lexicographical vs version sorting...")
    comp_v10 = ComponentDeclaration(
        component_id="demo.counter@v10",
        title="Counter V10",
        description="Lexicographically 'v10' comes after 'v2' in simple sort.",
        state_schema={},
        permissions=ComponentPermissions(readable=True),
    )
    registry.register_component(comp_v10)
    
    latest_comp_new = registry.get_component("demo.counter")
    print(f"New latest 'demo.counter': {latest_comp_new.title} (ID: {latest_comp_new.component_id})")

if __name__ == "__main__":
    run_example()
