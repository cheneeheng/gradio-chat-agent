
import pytest
from unittest.mock import MagicMock
from gradio_chat_agent.execution.engine import ExecutionEngine
from gradio_chat_agent.models.action import (
    ActionDeclaration,
    ActionPermission,
    ActionVisibility,
    ActionRisk
)
from gradio_chat_agent.models.intent import ChatIntent, IntentType
from gradio_chat_agent.models.state_snapshot import StateSnapshot
from gradio_chat_agent.persistence.in_memory import InMemoryStateRepository
from gradio_chat_agent.registry.in_memory import InMemoryRegistry

@pytest.fixture
def mock_registry():
    registry = InMemoryRegistry()
    
    # Action with cost 10
    registry.register_action(
        ActionDeclaration(
            action_id="test.expensive",
            title="Expensive Action",
            description="Costs 10 credits",
            targets=["test"],
            input_schema={},
            permission=ActionPermission(
                confirmation_required=False,
                risk=ActionRisk.LOW,
                visibility=ActionVisibility.USER
            ),
            cost=10.0
        ),
        handler=lambda inputs, snapshot: (snapshot.components, [], "Done")
    )
    
    # Action with default cost (1.0)
    registry.register_action(
        ActionDeclaration(
            action_id="test.cheap",
            title="Cheap Action",
            description="Costs 1 credit",
            targets=["test"],
            input_schema={},
            permission=ActionPermission(
                confirmation_required=False,
                risk=ActionRisk.LOW,
                visibility=ActionVisibility.USER
            )
        ),
        handler=lambda inputs, snapshot: (snapshot.components, [], "Done")
    )
    return registry

@pytest.fixture
def engine(mock_registry):
    repo = InMemoryStateRepository()
    # Set daily budget to 15
    repo.set_project_limits("test_project", {
        "limits": {
            "budget": {
                "daily": 15
            }
        }
    })
    repo.create_project("test_project", "Test Project")
    return ExecutionEngine(mock_registry, repo)

def test_budget_enforcement(engine):
    project_id = "test_project"
    
    # 1. Execute expensive action (Cost 10, Usage 0 -> 10)
    intent1 = ChatIntent(
        type=IntentType.ACTION_CALL,
        request_id="req1",
        action_id="test.expensive",
        execution_mode="assisted"
    )
    result1 = engine.execute_intent(project_id, intent1)
    assert result1.status == "success"
    assert result1.metadata["cost"] == 10.0
    
    usage = engine.repository.get_daily_budget_usage(project_id)
    assert usage == 10.0
    
    # 2. Execute cheap action (Cost 1, Usage 10 -> 11)
    intent2 = ChatIntent(
        type=IntentType.ACTION_CALL,
        request_id="req2",
        action_id="test.cheap",
        execution_mode="assisted"
    )
    result2 = engine.execute_intent(project_id, intent2)
    assert result2.status == "success"
    
    usage = engine.repository.get_daily_budget_usage(project_id)
    assert usage == 11.0
    
    # 3. Execute expensive action again (Cost 10, Usage 11 + 10 = 21 > 15) -> FAIL
    intent3 = ChatIntent(
        type=IntentType.ACTION_CALL,
        request_id="req3",
        action_id="test.expensive",
        execution_mode="assisted"
    )
    result3 = engine.execute_intent(project_id, intent3)
    assert result3.status == "rejected"
    assert result3.error.code == "budget_exceeded"
    
    # Usage should stay 11
    usage = engine.repository.get_daily_budget_usage(project_id)
    assert usage == 11.0

def test_budget_simulation_ignores_cost(engine):
    project_id = "test_project"
    
    # Even if budget is exceeded, simulation should pass (if we implemented it that way? 
    # Let's check logic: "if not simulate:" check for budget)
    
    # Exhaust budget first
    engine.repository.set_project_limits(project_id, {"limits": {"budget": {"daily": 1}}})
    engine.execute_intent(project_id, ChatIntent(
        type=IntentType.ACTION_CALL, request_id="setup", action_id="test.expensive"
    )) # Consumes 10, budget 1 -> should fail actually
    
    # Reset repo and set budget 0
    engine.repository._executions[project_id] = []
    engine.repository.set_project_limits(project_id, {"limits": {"budget": {"daily": 0}}})
    
    intent = ChatIntent(
        type=IntentType.ACTION_CALL,
        request_id="sim1",
        action_id="test.cheap", # Cost 1
        execution_mode="assisted"
    )
    
    # Execute with simulate=True
    result = engine.execute_intent(project_id, intent, simulate=True)
    assert result.status == "success"
    assert result.simulated is True
