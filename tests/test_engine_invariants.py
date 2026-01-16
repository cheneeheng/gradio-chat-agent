
import pytest
from gradio_chat_agent.execution.engine import ExecutionEngine
from gradio_chat_agent.models.action import (
    ActionDeclaration,
    ActionPermission,
    ActionVisibility,
    ActionRisk
)
from gradio_chat_agent.models.component import ComponentDeclaration, ComponentPermissions, ComponentInvariant
from gradio_chat_agent.models.intent import ChatIntent, IntentType
from gradio_chat_agent.persistence.in_memory import InMemoryStateRepository
from gradio_chat_agent.registry.in_memory import InMemoryRegistry

@pytest.fixture
def mock_registry():
    registry = InMemoryRegistry()
    
    # Component with invariant: value must be >= 0
    registry.register_component(
        ComponentDeclaration(
            component_id="test.counter",
            title="Counter",
            description="Positive counter",
            state_schema={"type": "object"},
            permissions=ComponentPermissions(readable=True),
            invariants=[
                ComponentInvariant(
                    description="Value must be non-negative",
                    expr="state['test.counter']['value'] >= 0"
                )
            ]
        )
    )
    
    # Action that sets value
    registry.register_action(
        ActionDeclaration(
            action_id="test.set",
            title="Set Value",
            description="Set value",
            targets=["test.counter"],
            input_schema={},
            permission=ActionPermission(
                confirmation_required=False,
                risk=ActionRisk.LOW,
                visibility=ActionVisibility.USER
            )
        ),
        handler=lambda inputs, snapshot: (
            {**snapshot.components, "test.counter": {"value": inputs["value"]}}, 
            [], 
            "Set"
        )
    )
    return registry

@pytest.fixture
def engine(mock_registry):
    repo = InMemoryStateRepository()
    repo.create_project("test_project", "Test Project")
    return ExecutionEngine(mock_registry, repo)

def test_invariant_enforcement(engine):
    project_id = "test_project"
    
    # 1. Set valid value (10)
    intent1 = ChatIntent(
        type=IntentType.ACTION_CALL,
        request_id="req1",
        action_id="test.set",
        inputs={"value": 10},
        execution_mode="assisted"
    )
    result1 = engine.execute_intent(project_id, intent1)
    assert result1.status == "success"
    
    # 2. Set invalid value (-5) -> FAIL
    intent2 = ChatIntent(
        type=IntentType.ACTION_CALL,
        request_id="req2",
        action_id="test.set",
        inputs={"value": -5},
        execution_mode="assisted"
    )
    result2 = engine.execute_intent(project_id, intent2)
    assert result2.status == "failed"
    assert result2.error.code == "invariant_violation"
    assert "Value must be non-negative" in result2.message

    # 3. Verify state was NOT updated (should still be 10)
    snapshot = engine.repository.get_latest_snapshot(project_id)
    assert snapshot.components["test.counter"]["value"] == 10
