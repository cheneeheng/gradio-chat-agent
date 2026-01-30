import pytest
from gradio_chat_agent.execution.engine import ExecutionEngine
from gradio_chat_agent.persistence.in_memory import InMemoryStateRepository
from gradio_chat_agent.registry.in_memory import InMemoryRegistry
from gradio_chat_agent.models.enums import IntentType, ActionRisk, ActionVisibility
from gradio_chat_agent.models.intent import ChatIntent
from gradio_chat_agent.models.action import ActionDeclaration, ActionPermission

class TestReconstruction:
    @pytest.fixture
    def setup(self):
        registry = InMemoryRegistry()
        repository = InMemoryStateRepository()
        engine = ExecutionEngine(registry, repository)
        project_id = "p1"
        
        # Action that sets a nested dict
        action = ActionDeclaration(
            action_id="set", title="S", description="D", targets=["t"], 
            input_schema={},
            permission=ActionPermission(confirmation_required=False, risk=ActionRisk.LOW, visibility=ActionVisibility.USER)
        )
        def handler(inputs, snapshot):
            return {"comp": inputs}, [], "ok"
        registry.register_action(action, handler)
        
        return engine, project_id

    def test_reconstruct_basic(self, setup):
        engine, pid = setup
        
        engine.execute_intent(pid, ChatIntent(type=IntentType.ACTION_CALL, request_id="1", action_id="set", inputs={"v": 1}), user_roles=["admin"])
        engine.execute_intent(pid, ChatIntent(type=IntentType.ACTION_CALL, request_id="2", action_id="set", inputs={"v": 2}), user_roles=["admin"])
        
        state = engine.reconstruct_state(pid, target_request_id="1")
        assert state["comp"]["v"] == 1
        
        state_full = engine.reconstruct_state(pid)
        assert state_full["comp"]["v"] == 2

    def test_reconstruct_timestamp(self, setup):
        engine, pid = setup
        from datetime import datetime, timezone, timedelta
        
        t1 = datetime.now(timezone.utc)
        engine.execute_intent(pid, ChatIntent(type=IntentType.ACTION_CALL, request_id="1", action_id="set", inputs={"v": 1}), user_roles=["admin"])
        
        time_limit = datetime.now(timezone.utc)
        
        engine.execute_intent(pid, ChatIntent(type=IntentType.ACTION_CALL, request_id="2", action_id="set", inputs={"v": 2}), user_roles=["admin"])
        
        state = engine.reconstruct_state(pid, target_timestamp=time_limit)
        assert state["comp"]["v"] == 1

    def test_reconstruct_naive_timestamp(self, setup):
        engine, pid = setup
        from datetime import datetime
        
        engine.execute_intent(pid, ChatIntent(type=IntentType.ACTION_CALL, request_id="1", action_id="set", inputs={"v": 10}), user_roles=["admin"])
        
        # Naive timestamp
        limit = datetime.now()
        
        state = engine.reconstruct_state(pid, target_timestamp=limit)
        assert state["comp"]["v"] == 10

    def test_reconstruct_component_removal(self, setup):
        engine, pid = setup
        from gradio_chat_agent.models.execution_result import ExecutionResult, StateDiffEntry
        from gradio_chat_agent.models.enums import ExecutionStatus, StateDiffOp
        
        # Manually save a result with removal
        res = ExecutionResult(
            request_id="r1", action_id="a", status=ExecutionStatus.SUCCESS, 
            state_snapshot_id="s1", 
            state_diff=[StateDiffEntry(path="comp", op=StateDiffOp.REMOVE)]
        )
        engine.repository.save_execution(pid, res)
        
        state = engine.reconstruct_state(pid)
        assert "comp" not in state

    def test_reconstruct_attr_removal(self, setup):
        engine, pid = setup
        from gradio_chat_agent.models.execution_result import ExecutionResult, StateDiffEntry
        from gradio_chat_agent.models.enums import ExecutionStatus, StateDiffOp
        
        # Initial
        engine.execute_intent(pid, ChatIntent(type=IntentType.ACTION_CALL, request_id="1", action_id="set", inputs={"a": 1}))
        
        # Remove attr 'a'
        res = ExecutionResult(
            request_id="r2", action_id="a", status=ExecutionStatus.SUCCESS, 
            state_snapshot_id="s2", 
            state_diff=[StateDiffEntry(path="comp.a", op=StateDiffOp.REMOVE)]
        )
        engine.repository.save_execution(pid, res)
        
        state = engine.reconstruct_state(pid)
        assert "a" not in state["comp"]
