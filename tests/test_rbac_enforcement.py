import pytest
from gradio_chat_agent.execution.engine import ExecutionEngine
from gradio_chat_agent.models.enums import IntentType, ActionRisk, ActionVisibility
from gradio_chat_agent.models.intent import ChatIntent
from gradio_chat_agent.models.action import ActionDeclaration, ActionPermission
from gradio_chat_agent.persistence.in_memory import InMemoryStateRepository
from gradio_chat_agent.registry.in_memory import InMemoryRegistry

class TestRBACEnforcement:
    @pytest.fixture
    def setup(self):
        registry = InMemoryRegistry()
        repository = InMemoryStateRepository()
        engine = ExecutionEngine(registry, repository)
        project_id = "test-proj"
        
        # Low risk action
        low_action = ActionDeclaration(
            action_id="test.low", title="L", description="L", targets=["t"], 
            input_schema={},
            permission=ActionPermission(confirmation_required=False, risk=ActionRisk.LOW, visibility=ActionVisibility.USER)
        )
        registry.register_action(low_action, lambda i, s: ({}, [], "ok"))

        # Medium risk action
        med_action = ActionDeclaration(
            action_id="test.med", title="M", description="M", targets=["t"], 
            input_schema={},
            permission=ActionPermission(confirmation_required=False, risk=ActionRisk.MEDIUM, visibility=ActionVisibility.USER)
        )
        registry.register_action(med_action, lambda i, s: ({}, [], "ok"))

        # High risk action
        high_action = ActionDeclaration(
            action_id="test.high", title="H", description="H", targets=["t"], 
            input_schema={},
            permission=ActionPermission(confirmation_required=True, risk=ActionRisk.HIGH, visibility=ActionVisibility.USER)
        )
        registry.register_action(high_action, lambda i, s: ({}, [], "ok"))
        
        return engine, project_id

    def test_viewer_rejected(self, setup):
        engine, pid = setup
        intent = ChatIntent(type=IntentType.ACTION_CALL, request_id="r1", action_id="test.low")
        res = engine.execute_intent(pid, intent, user_roles=["viewer"])
        assert res.status == "rejected"
        assert "viewer" in res.message

    def test_no_roles_rejected(self, setup):
        engine, pid = setup
        intent = ChatIntent(type=IntentType.ACTION_CALL, request_id="r1", action_id="test.low")
        res = engine.execute_intent(pid, intent, user_roles=[])
        assert res.status == "rejected"
        assert "viewer" in res.message

    def test_operator_low_success(self, setup):
        engine, pid = setup
        intent = ChatIntent(type=IntentType.ACTION_CALL, request_id="r1", action_id="test.low")
        res = engine.execute_intent(pid, intent, user_roles=["operator"])
        assert res.status == "success"

    def test_operator_med_success(self, setup):
        engine, pid = setup
        intent = ChatIntent(type=IntentType.ACTION_CALL, request_id="r1", action_id="test.med")
        res = engine.execute_intent(pid, intent, user_roles=["operator"])
        assert res.status == "success"

    def test_operator_high_rejected(self, setup):
        engine, pid = setup
        intent = ChatIntent(type=IntentType.ACTION_CALL, request_id="r1", action_id="test.high", confirmed=True)
        res = engine.execute_intent(pid, intent, user_roles=["operator"])
        assert res.status == "rejected"
        assert "operator" in res.message

    def test_admin_high_success(self, setup):
        engine, pid = setup
        intent = ChatIntent(type=IntentType.ACTION_CALL, request_id="r1", action_id="test.high", confirmed=True)
        res = engine.execute_intent(pid, intent, user_roles=["admin"])
        assert res.status == "success"

    def test_unknown_role_rejected(self, setup):
        engine, pid = setup
        intent = ChatIntent(type=IntentType.ACTION_CALL, request_id="r1", action_id="test.low")
        res = engine.execute_intent(pid, intent, user_roles=["stranger"])
        assert res.status == "rejected"
        assert "unknown" in res.message
