"""Example of Deeply Nested State Reconstruction.

This example demonstrates:
1. Components with deeply nested state (3+ levels).
2. How the diffing engine handles specific sub-field updates.
3. Successful reconstruction of complex hierarchies.
"""

from gradio_chat_agent.execution.engine import ExecutionEngine
from gradio_chat_agent.persistence.in_memory import InMemoryStateRepository
from gradio_chat_agent.registry.in_memory import InMemoryRegistry
from gradio_chat_agent.models.intent import ChatIntent
from gradio_chat_agent.models.enums import IntentType, ActionRisk, ActionVisibility
from gradio_chat_agent.models.action import ActionDeclaration, ActionPermission

def run_example():
    # 1. Setup
    registry = InMemoryRegistry()
    repository = InMemoryStateRepository()
    engine = ExecutionEngine(registry, repository)
    project_id = "nest-demo"

    # 2. Register a complex component
    # State: { "app": { "settings": { "ui": { "theme": "dark" } } } }
    def nested_handler(inputs, snapshot):
        new_theme = inputs["theme"]
        new_comps = snapshot.components.copy()
        
        # Deep update
        state = new_comps.get("complex.sys", {"app": {"settings": {"ui": {"theme": "light"}}}}).copy()
        state["app"]["settings"]["ui"]["theme"] = new_theme
        new_comps["complex.sys"] = state
        
        return new_comps, [], f"Theme set to {new_theme}"

    registry.register_action(
        ActionDeclaration(
            action_id="theme.set", title="T", description="T", targets=["complex.sys"],
            input_schema={"type": "object", "properties": {"theme": {"type": "string"}}},
            permission=ActionPermission(confirmation_required=False, risk=ActionRisk.LOW, visibility=ActionVisibility.USER)
        ),
        handler=nested_handler
    )

    # 3. Perform a sequence of updates
    print("Step 1: Set theme to 'dark'")
    engine.execute_intent(project_id, ChatIntent(type=IntentType.ACTION_CALL, request_id="r1", action_id="theme.set", inputs={"theme": "dark"}))
    
    print("Step 2: Set theme to 'high-contrast'")
    engine.execute_intent(project_id, ChatIntent(type=IntentType.ACTION_CALL, request_id="r2", action_id="theme.set", inputs={"theme": "high-contrast"}))

    # 4. Verify Reconstruction
    print("\n--- Reconstructing Deep State ---")
    reconstructed = engine.reconstruct_state(project_id)
    
    # Access deep value
    try:
        theme = reconstructed["complex.sys"]["app"]["settings"]["ui"]["theme"]
        print(f"Reconstructed Theme: {theme} (Expected: high-contrast)")
        assert theme == "high-contrast"
        print("SUCCESS: Deep state hierarchy correctly reconstructed.")
    except KeyError as e:
        print(f"FAILURE: Could not navigate reconstructed state: Missing key {e}")

if __name__ == "__main__":
    run_example()
