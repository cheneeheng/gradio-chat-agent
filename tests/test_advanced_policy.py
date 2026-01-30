import pytest
from gradio_chat_agent.execution.engine import ExecutionEngine
from gradio_chat_agent.persistence.in_memory import InMemoryStateRepository
from gradio_chat_agent.registry.in_memory import InMemoryRegistry
from gradio_chat_agent.models.action import ActionDeclaration, ActionPermission
from gradio_chat_agent.models.intent import ChatIntent
from gradio_chat_agent.models.enums import IntentType, ExecutionStatus
from gradio_chat_agent.models.state_snapshot import StateSnapshot

class TestAdvancedPolicy:
    @pytest.fixture
    def setup(self):
        registry = InMemoryRegistry()
        repository = InMemoryStateRepository()
        engine = ExecutionEngine(registry, repository)
        project_id = "test-p"
        repository.create_project(project_id, "Test")
        
        registry.register_action(
            ActionDeclaration(
                action_id="test.act", title="T", description="D", targets=["t"], 
                input_schema={"type": "object", "properties": {"val": {"type": "integer"}}},
                permission=ActionPermission(confirmation_required=False, risk="low", visibility="user")
            ),
            handler=lambda i, s: ({}, [], "ok")
        )
        
        return engine, repository, project_id

    def test_policy_rule_rejection(self, setup):
        engine, repo, pid = setup
        repo.set_project_limits(pid, {
            "rules": [
                {
                    "id": "block_val_13",
                    "condition": "inputs.get('val') == 13",
                    "effect": "reject",
                    "message": "Value 13 is unlucky."
                }
            ]
        })
        
        intent = ChatIntent(type=IntentType.ACTION_CALL, request_id="r1", action_id="test.act", inputs={"val": 13})
        res = engine.execute_intent(pid, intent, user_roles=["admin"])
        
        assert res.status == ExecutionStatus.REJECTED
        assert "unlucky" in res.message

    def test_policy_rule_require_approval(self, setup):
        engine, repo, pid = setup
        repo.set_project_limits(pid, {
            "rules": [
                {
                    "id": "approval_rule",
                    "condition": "inputs.get('val') > 100",
                    "effect": "require_approval",
                    "message": "Too high."
                }
            ]
        })
        
        intent = ChatIntent(type=IntentType.ACTION_CALL, request_id="r1", action_id="test.act", inputs={"val": 500})
        res = engine.execute_intent(pid, intent, user_roles=["admin"])
        
        assert res.status == ExecutionStatus.PENDING_APPROVAL
        assert "Too high" in res.message
        
        # Verify it succeeds when confirmed
        intent.confirmed = True
        res2 = engine.execute_intent(pid, intent, user_roles=["admin"])
        assert res2.status == ExecutionStatus.SUCCESS

    def test_policy_rule_with_user_proxy(self, setup):
        engine, repo, pid = setup
        repo.create_user("alice", "h", organization_id="restricted_org")
        repo.set_project_limits(pid, {
            "rules": [
                {
                    "id": "block_org",
                    "condition": "user.organization_id == 'restricted_org'",
                    "effect": "reject"
                }
            ]
        })
        
        intent = ChatIntent(type=IntentType.ACTION_CALL, request_id="r1", action_id="test.act")
        res = engine.execute_intent(pid, intent, user_id="alice", user_roles=["viewer"])
        
        assert res.status == ExecutionStatus.REJECTED
        assert "block_org" in res.message

    def test_policy_rule_safe_eval_error(self, setup):
        engine, repo, pid = setup
        repo.set_project_limits(pid, {
            "rules": [{"id": "err", "condition": "1/0", "effect": "reject"}]
        })
        
        intent = ChatIntent(type=IntentType.ACTION_CALL, request_id="r1", action_id="test.act")
        # Should NOT reject if rule evaluation fails (logs warning)
        res = engine.execute_intent(pid, intent, user_roles=["admin"])
        assert res.status == ExecutionStatus.SUCCESS

    def test_policy_rule_invalid_rule_structure(self, setup):
        engine, repo, pid = setup
        repo.set_project_limits(pid, {
            "rules": [{"id": "incomplete"}] # Missing condition/effect
        })
        intent = ChatIntent(type=IntentType.ACTION_CALL, request_id="r1", action_id="test.act")
        res = engine.execute_intent(pid, intent, user_roles=["admin"])
        assert res.status == ExecutionStatus.SUCCESS

    def test_policy_rule_no_user_in_context(self, setup):
        engine, repo, pid = setup
        repo.set_project_limits(pid, {
            "rules": [{"id": "check_user", "condition": "user is None", "effect": "reject"}]
        })
        intent = ChatIntent(type=IntentType.ACTION_CALL, request_id="r1", action_id="test.act")
        # Call without user_id
        res = engine.execute_intent(pid, intent, user_roles=["admin"])
        assert res.status == ExecutionStatus.REJECTED

    def test_policy_rule_user_not_found(self, setup):
        engine, repo, pid = setup
        repo.set_project_limits(pid, {
            "rules": [{"id": "check_user", "condition": "user is None", "effect": "reject"}]
        })
        intent = ChatIntent(type=IntentType.ACTION_CALL, request_id="r1", action_id="test.act")
        # Call with user_id that doesn't exist in repo
        res = engine.execute_intent(pid, intent, user_id="ghost", user_roles=["admin"])
        assert res.status == ExecutionStatus.REJECTED
