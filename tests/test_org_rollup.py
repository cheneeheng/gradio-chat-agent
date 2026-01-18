import pytest
from gradio_chat_agent.api.endpoints import ApiEndpoints
from gradio_chat_agent.execution.engine import ExecutionEngine
from gradio_chat_agent.persistence.in_memory import InMemoryStateRepository
from gradio_chat_agent.persistence.sql_repository import SQLStateRepository
from gradio_chat_agent.registry.in_memory import InMemoryRegistry
from gradio_chat_agent.models.intent import ChatIntent
from gradio_chat_agent.models.enums import IntentType, ExecutionStatus, ActionRisk, ActionVisibility
from gradio_chat_agent.models.action import ActionDeclaration, ActionPermission

class TestOrgRollup:
    @pytest.fixture
    def setup_in_memory(self):
        repo = InMemoryStateRepository()
        engine = ExecutionEngine(InMemoryRegistry(), repo)
        api = ApiEndpoints(engine)
        
        # Action with cost
        action = ActionDeclaration(
            action_id="test.act", title="T", description="D", targets=["t"], 
            input_schema={}, cost=10.0,
            permission=ActionPermission(confirmation_required=False, risk=ActionRisk.LOW, visibility=ActionVisibility.USER)
        )
        engine.registry.register_action(action, lambda i, s: ({}, [], "ok"))
        
        return api, engine, repo

    def test_in_memory_rollup(self, setup_in_memory):
        api, engine, repo = setup_in_memory
        
        repo.create_project("p1", "P1")
        repo.create_project("p2", "P2")
        
        # P1: 2 successes
        engine.execute_intent("p1", ChatIntent(type=IntentType.ACTION_CALL, request_id="r1", action_id="test.act"), user_roles=["admin"])
        engine.execute_intent("p1", ChatIntent(type=IntentType.ACTION_CALL, request_id="r2", action_id="test.act"), user_roles=["admin"])
        
        # P2: 1 success, 1 failure (missing action)
        engine.execute_intent("p2", ChatIntent(type=IntentType.ACTION_CALL, request_id="r3", action_id="test.act"), user_roles=["admin"])
        engine.execute_intent("p2", ChatIntent(type=IntentType.ACTION_CALL, request_id="r4", action_id="missing"), user_roles=["admin"])
        
        res = api.api_org_rollup(user_id="admin")
        assert res["code"] == 0
        data = res["data"]
        
        assert data["total_projects"] == 2
        assert data["total_executions"] == 4
        assert data["total_cost"] == 30.0 # 3 successes * 10.0
        
        p1 = data["projects"]["p1"]
        assert p1["success_count"] == 2
        assert p1["total_cost"] == 20.0
        
        p2 = data["projects"]["p2"]
        assert p2["success_count"] == 1
        assert p2["rejected_count"] == 1
        assert p2["total_cost"] == 10.0

    def test_sql_rollup(self):
        repo = SQLStateRepository("sqlite:///:memory:")
        engine = ExecutionEngine(InMemoryRegistry(), repo)
        api = ApiEndpoints(engine)
        
        action = ActionDeclaration(
            action_id="test.act", title="T", description="D", targets=["t"], 
            input_schema={}, cost=5.0,
            permission=ActionPermission(confirmation_required=False, risk=ActionRisk.LOW, visibility=ActionVisibility.USER)
        )
        engine.registry.register_action(action, lambda i, s: ({}, [], "ok"))
        
        repo.create_project("p1", "P1")
        engine.execute_intent("p1", ChatIntent(type=IntentType.ACTION_CALL, request_id="r1", action_id="test.act"), user_roles=["admin"])
        
        res = api.api_org_rollup(user_id="admin")
        data = res["data"]
        assert data["total_projects"] >= 1 # default_project might be there
        assert data["projects"]["p1"]["total_cost"] == 5.0

    def test_api_unauthorized(self, setup_in_memory):
        api, _, _ = setup_in_memory
        res = api.api_org_rollup(user_id="alice")
        assert res["code"] == 1
        assert "Permission denied" in res["message"]
