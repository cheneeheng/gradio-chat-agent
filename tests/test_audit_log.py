import pytest
from gradio_chat_agent.execution.engine import ExecutionEngine
from gradio_chat_agent.models.enums import IntentType, ActionRisk, ActionVisibility
from gradio_chat_agent.models.intent import ChatIntent
from gradio_chat_agent.models.action import ActionDeclaration, ActionPermission
from gradio_chat_agent.persistence.sql_repository import SQLStateRepository
from gradio_chat_agent.registry.in_memory import InMemoryRegistry

def test_full_intent_logging(tmp_path):
    db_file = tmp_path / "test_audit.db"
    repo = SQLStateRepository(f"sqlite:///{db_file}")
    registry = InMemoryRegistry()
    engine = ExecutionEngine(registry, repo)
    project_id = "test-p"
    
    # Register action
    action = ActionDeclaration(
        action_id="test.act",
        title="T",
        description="D",
        targets=["t"],
        input_schema={"type": "object", "properties": {"val": {"type": "integer"}}},
        permission=ActionPermission(confirmation_required=False, risk=ActionRisk.LOW, visibility=ActionVisibility.USER)
    )
    registry.register_action(action, lambda i, s: ({}, [], "ok"))
    
    # Execute intent
    intent = ChatIntent(
        type=IntentType.ACTION_CALL,
        request_id="req-1",
        action_id="test.act",
        inputs={"val": 42},
        trace={"meta": "data"}
    )
    engine.execute_intent(project_id, intent)
    
    # Verify audit log contains full intent
    history = repo.get_execution_history(project_id)
    assert len(history) == 1
    logged_intent = history[0].intent
    assert logged_intent is not None
    assert logged_intent["action_id"] == "test.act"
    assert logged_intent["inputs"] == {"val": 42}
    assert logged_intent["trace"] == {"meta": "data"}

def test_execution_metadata_logging(tmp_path):
    db_file = tmp_path / "test_metadata.db"
    repo = SQLStateRepository(f"sqlite:///{db_file}")
    registry = InMemoryRegistry()
    engine = ExecutionEngine(registry, repo)
    project_id = "test-p"
    user_id = "alice"
    
    # Register action with custom cost
    action = ActionDeclaration(
        action_id="test.act",
        title="T",
        description="D",
        targets=["t"],
        input_schema={},
        permission=ActionPermission(confirmation_required=False, risk=ActionRisk.LOW, visibility=ActionVisibility.USER),
        cost=5.5
    )
    registry.register_action(action, lambda i, s: ({}, [], "ok"))
    
    # Execute intent
    intent = ChatIntent(
        type=IntentType.ACTION_CALL,
        request_id="req-1",
        action_id="test.act"
    )
    engine.execute_intent(project_id, intent, user_id=user_id)
    
    # Verify audit log contains metadata
    history = repo.get_execution_history(project_id)
    assert len(history) == 1
    result = history[0]
    assert result.user_id == user_id
    assert result.cost == 5.5
    assert result.execution_time_ms is not None
    assert result.execution_time_ms > 0
