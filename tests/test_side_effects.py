import pytest
from unittest.mock import MagicMock
from gradio_chat_agent.execution.engine import ExecutionEngine
from gradio_chat_agent.models.enums import IntentType, ActionRisk, ActionVisibility
from gradio_chat_agent.models.intent import ChatIntent
from gradio_chat_agent.models.action import ActionDeclaration, ActionPermission
from gradio_chat_agent.persistence.in_memory import InMemoryStateRepository
from gradio_chat_agent.registry.in_memory import InMemoryRegistry

class TestSideEffects:
    @pytest.fixture
    def setup(self):
        registry = InMemoryRegistry()
        repository = InMemoryStateRepository()
        engine = ExecutionEngine(registry, repository)
        project_id = "test-proj"
        
        # Register dummy action
        action = ActionDeclaration(
            action_id="test.act",
            title="T",
            description="D",
            targets=["t"],
            input_schema={},
            permission=ActionPermission(confirmation_required=False, risk=ActionRisk.LOW, visibility=ActionVisibility.USER)
        )
        registry.register_action(action, lambda i, s: ({}, [], "ok"))
        
        return engine, project_id

    def test_hook_triggered_on_success(self, setup):
        engine, pid = setup
        hook = MagicMock()
        engine.add_post_execution_hook(hook)
        
        intent = ChatIntent(type=IntentType.ACTION_CALL, request_id="r1", action_id="test.act")
        engine.execute_intent(pid, intent, user_roles=["admin"])
        
        hook.assert_called_once()
        args, _ = hook.call_args
        assert args[0] == pid
        assert args[1].action_id == "test.act"

    def test_hook_not_triggered_on_simulation(self, setup):
        engine, pid = setup
        hook = MagicMock()
        engine.add_post_execution_hook(hook)
        
        intent = ChatIntent(type=IntentType.ACTION_CALL, request_id="r1", action_id="test.act")
        engine.execute_intent(pid, intent, simulate=True, user_roles=["admin"])
        
        hook.assert_not_called()

    def test_hook_not_triggered_on_rejection(self, setup):
        engine, pid = setup
        hook = MagicMock()
        engine.add_post_execution_hook(hook)
        
        # Missing action_id causes rejection
        intent = ChatIntent(type=IntentType.ACTION_CALL, request_id="r1", action_id="missing")
        engine.execute_intent(pid, intent, user_roles=["admin"])
        
        hook.assert_not_called()

    def test_hook_exception_logged_but_not_raised(self, setup):
        engine, pid = setup
        hook = MagicMock(side_effect=ValueError("Hook crashed"))
        engine.add_post_execution_hook(hook)
        
        intent = ChatIntent(type=IntentType.ACTION_CALL, request_id="r1", action_id="test.act")
        # Should not raise exception
        res = engine.execute_intent(pid, intent, user_roles=["admin"])
        assert res.status == "success"
        hook.assert_called_once()

    def test_revert_triggers_hook(self, setup):
        engine, pid = setup
        # Create a snapshot to revert to
        from gradio_chat_agent.models.state_snapshot import StateSnapshot
        snap = StateSnapshot(snapshot_id="s1", components={})
        engine.repository.save_snapshot(pid, snap)
        
        hook = MagicMock()
        engine.add_post_execution_hook(hook)
        
        engine.revert_to_snapshot(pid, "s1")
        hook.assert_called_once()
        args, _ = hook.call_args
        assert args[1].action_id == "system.revert"

    def test_dispatch_post_execution_unreachable_branches(self, setup):
        engine, pid = setup
        hook = MagicMock()
        engine.add_post_execution_hook(hook)
        
        from gradio_chat_agent.models.execution_result import ExecutionResult, ExecutionStatus
        
        # 1. Simulated
        res_sim = ExecutionResult(request_id="1", action_id="a", status=ExecutionStatus.SUCCESS, state_snapshot_id="s", simulated=True)
        engine._dispatch_post_execution(pid, res_sim)
        hook.assert_not_called()
        
        # 2. Not Success
        res_fail = ExecutionResult(request_id="2", action_id="a", status=ExecutionStatus.FAILED, state_snapshot_id="s")
        engine._dispatch_post_execution(pid, res_fail)
        hook.assert_not_called()