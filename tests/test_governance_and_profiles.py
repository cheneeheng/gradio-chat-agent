import pytest
from gradio_chat_agent.execution.engine import ExecutionEngine
from gradio_chat_agent.models.enums import IntentType, ActionRisk, ActionVisibility
from gradio_chat_agent.models.intent import ChatIntent
from gradio_chat_agent.models.action import ActionDeclaration, ActionPermission
from gradio_chat_agent.persistence.in_memory import InMemoryStateRepository
from gradio_chat_agent.registry.in_memory import InMemoryRegistry

class TestGovernanceAndProfiles:
    @pytest.fixture
    def setup(self):
        registry = InMemoryRegistry()
        repository = InMemoryStateRepository()
        engine = ExecutionEngine(registry, repository)
        project_id = "test-p"
        
        action = ActionDeclaration(
            action_id="test.act", title="T", description="D", targets=["t"], 
            input_schema={}, cost=10.0,
            permission=ActionPermission(confirmation_required=False, risk=ActionRisk.LOW, visibility=ActionVisibility.USER)
        )
        registry.register_action(action, lambda i, s: ({}, [], "ok"))
        
        return engine, repository, project_id

    def test_governance_restored_rate_limit(self, setup):
        engine, repo, pid = setup
        repo.set_project_limits(pid, {"limits": {"rate": {"per_minute": 1}}})
        
        intent = ChatIntent(type=IntentType.ACTION_CALL, request_id="r1", action_id="test.act")
        
        # 1st: success (using admin role to pass RBAC)
        assert engine.execute_intent(pid, intent, user_roles=["admin"]).status == "success"
        # 2nd: rejected (rate limit)
        res = engine.execute_intent(pid, intent, user_roles=["admin"])
        assert res.status == "rejected"
        assert res.error.code == "rate_limit"

    def test_governance_restored_budget(self, setup):
        engine, repo, pid = setup
        repo.set_project_limits(pid, {"limits": {"budget": {"daily": 15.0}}})
        
        intent = ChatIntent(type=IntentType.ACTION_CALL, request_id="r1", action_id="test.act")
        
        # 1st: success (cost 10, using admin role to pass RBAC)
        assert engine.execute_intent(pid, intent, user_roles=["admin"]).status == "success"
        # 2nd: rejected (cost 10 + 10 > 15)
        res = engine.execute_intent(pid, intent, user_roles=["admin"])
        assert res.status == "rejected"
        assert res.error.code == "budget_exceeded"

    def test_user_profile_fields(self, setup):
        _, repo, _ = setup
        repo.create_user("u1", "h1", "Full Name", "email@example.com", "org123")
        
        user = repo.get_user("u1")
        assert user["full_name"] == "Full Name"
        assert user["email"] == "email@example.com"
        assert user["organization_id"] == "org123"

    def test_user_profile_sql(self):
        from gradio_chat_agent.persistence.sql_repository import SQLStateRepository
        repo = SQLStateRepository("sqlite:///:memory:")
        repo.create_user("u1", "h1", "Full Name", "email@example.com", "org123")
        
        user = repo.get_user("u1")
        assert user["full_name"] == "Full Name"
        assert user["email"] == "email@example.com"
        assert user["organization_id"] == "org123"
