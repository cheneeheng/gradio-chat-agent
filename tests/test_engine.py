import uuid
from typing import Any
from unittest.mock import MagicMock

import pytest
from gradio_chat_agent.execution.engine import ExecutionEngine
from gradio_chat_agent.models.action import (
    ActionDeclaration,
    ActionPermission,
    ActionPrecondition,
)
from gradio_chat_agent.models.component import (
    ComponentDeclaration,
    ComponentPermissions,
)
from gradio_chat_agent.models.enums import (
    ActionRisk,
    ActionVisibility,
    ExecutionMode,
    ExecutionStatus,
    IntentType,
)
from gradio_chat_agent.models.intent import ChatIntent, IntentMedia
from gradio_chat_agent.models.plan import ExecutionPlan
from gradio_chat_agent.models.state_snapshot import StateSnapshot
from gradio_chat_agent.persistence.in_memory import InMemoryStateRepository
from gradio_chat_agent.registry.in_memory import InMemoryRegistry


class TestEngine:
    @pytest.fixture
    def setup(self):
        registry = InMemoryRegistry()
        repository = InMemoryStateRepository()
        engine = ExecutionEngine(registry, repository)
        project_id = "proj-1"

        # Setup Counter Component
        comp = ComponentDeclaration(
            component_id="demo.counter",
            title="Counter",
            description="A number",
            state_schema={"type": "object", "properties": {"value": {"type": "integer"}}},
            permissions=ComponentPermissions(readable=True),
        )
        registry.register_component(comp)

        # Setup Set Action
        action_set = ActionDeclaration(
            action_id="demo.counter.set",
            title="Set Counter",
            description="Sets the value",
            targets=["demo.counter"],
            input_schema={
                "type": "object",
                "properties": {"value": {"type": "integer"}},
                "required": ["value"],
            },
            permission=ActionPermission(
                confirmation_required=False,
                risk=ActionRisk.LOW,
                visibility=ActionVisibility.USER,
            ),
        )

        def set_handler(inputs, snapshot):
            new_comps = snapshot.components.copy()
            new_comps["demo.counter"] = {"value": inputs["value"]}
            return new_comps, [], f"Set to {inputs['value']}"

        registry.register_action(action_set, set_handler)

        return engine, registry, repository, project_id

    def test_execute_success(self, setup):
        engine, _, repo, pid = setup
        
        # Initial state
        repo.save_snapshot(pid, StateSnapshot(snapshot_id="0", components={"demo.counter": {"value": 0}}))

        intent = ChatIntent(
            type=IntentType.ACTION_CALL,
            request_id="req-1",
            action_id="demo.counter.set",
            inputs={"value": 10},
        )

        result = engine.execute_intent(pid, intent)
        assert result.status == ExecutionStatus.SUCCESS
        # Diff recurses to the leaf
        assert result.state_diff[0].value == 10
        assert result.state_diff[0].path == "demo.counter.value"
        
        # Verify persistence
        history = repo.get_execution_history(pid)
        assert len(history) == 1
        assert history[0].status == ExecutionStatus.SUCCESS

    def test_execute_missing_action(self, setup):
        engine, _, _, pid = setup
        intent = ChatIntent(
            type=IntentType.ACTION_CALL,
            request_id="req-1",
            action_id="missing.action",
        )
        result = engine.execute_intent(pid, intent)
        assert result.status == ExecutionStatus.REJECTED
        assert "not found" in result.message

    def test_execute_validation_error(self, setup):
        engine, _, _, pid = setup
        intent = ChatIntent(
            type=IntentType.ACTION_CALL,
            request_id="req-1",
            action_id="demo.counter.set",
            inputs={"value": "not an integer"}, # Schema expects integer
        )
        result = engine.execute_intent(pid, intent)
        assert result.status == ExecutionStatus.REJECTED
        assert "validation failed" in result.message

    def test_execute_confirmation_required(self, setup):
        engine, registry, _, pid = setup
        
        # Register dangerous action
        action_nuke = ActionDeclaration(
            action_id="demo.nuke",
            title="Nuke",
            description="Destroy",
            targets=["demo.counter"],
            input_schema={},
            permission=ActionPermission(
                confirmation_required=True, # Critical
                risk=ActionRisk.HIGH,
                visibility=ActionVisibility.USER,
            ),
        )
        registry.register_action(action_nuke, lambda i, s: ({}, [], "Boom"))

        # Try without confirmation
        intent = ChatIntent(
            type=IntentType.ACTION_CALL,
            request_id="req-1",
            action_id="demo.nuke",
            execution_mode="autonomous",
            confirmed=False
        )
        
        # Should be rejected because HIGH risk requires confirmation (and admin role, but let's assume default viewer role first)
        result = engine.execute_intent(pid, intent, user_roles=["viewer"])
        assert result.status == ExecutionStatus.REJECTED
        
        # Try with admin but no confirmation
        result = engine.execute_intent(pid, intent, user_roles=["admin"])
        assert result.status == ExecutionStatus.REJECTED
        assert result.error.code == "confirmation_required"

        # Try with confirmation
        intent.confirmed = True
        result = engine.execute_intent(pid, intent, user_roles=["admin"])
        assert result.status == ExecutionStatus.SUCCESS

    def test_precondition_check(self, setup):
        engine, registry, repo, pid = setup
        
        # Action that requires counter > 5
        action_dec = ActionDeclaration(
            action_id="demo.decrement",
            title="Decrement",
            description="Lower it",
            targets=["demo.counter"],
            input_schema={},
            preconditions=[
                ActionPrecondition(
                    id="check.val",
                    description="Value must be > 5",
                    expr="state['demo.counter']['value'] > 5"
                )
            ],
            permission=ActionPermission(
                confirmation_required=False, risk=ActionRisk.LOW, visibility=ActionVisibility.USER
            )
        )
        registry.register_action(action_dec, lambda i, s: ({}, [], "ok"))

        # Set state to 0
        repo.save_snapshot(pid, StateSnapshot(snapshot_id="0", components={"demo.counter": {"value": 0}}))

        intent = ChatIntent(
            type=IntentType.ACTION_CALL,
            request_id="req-1",
            action_id="demo.decrement",
        )
        
        result = engine.execute_intent(pid, intent)
        assert result.status == ExecutionStatus.REJECTED
        assert "Precondition failed" in result.message

        # Set state to 10
        repo.save_snapshot(pid, StateSnapshot(snapshot_id="1", components={"demo.counter": {"value": 10}}))
        
        result = engine.execute_intent(pid, intent)
        assert result.status == ExecutionStatus.SUCCESS

    def test_execute_invalid_intent_type(self, setup):
        engine, _, _, pid = setup
        intent = ChatIntent(
            type=IntentType.CLARIFICATION_REQUEST,
            request_id="req-1",
            question="What?"
        )
        result = engine.execute_intent(pid, intent)
        assert result.status == ExecutionStatus.REJECTED
        assert "only executes action_call" in result.message

    def test_execute_missing_action_id(self, setup):
        engine, _, _, pid = setup
        # Hack to create intent with None action_id (Pydantic might allow if Optional, but we validate later)
        # Actually ChatIntent action_id is Optional, defaulting to None.
        intent = ChatIntent(
            type=IntentType.ACTION_CALL,
            request_id="req-1",
            # action_id is None by default
        )
        result = engine.execute_intent(pid, intent)
        assert result.status == ExecutionStatus.REJECTED
        assert "Missing action_id" in result.message

    def test_handler_error(self, setup):
        engine, registry, _, pid = setup
        
        action_broken = ActionDeclaration(
            action_id="demo.broken",
            title="Broken",
            description="Fails",
            targets=["demo.counter"],
            input_schema={},
            permission=ActionPermission(
                confirmation_required=False, risk=ActionRisk.LOW, visibility=ActionVisibility.USER
            )
        )
        def broken_handler(inputs, snapshot):
            raise ValueError("Something went wrong")

        registry.register_action(action_broken, broken_handler)
        
        intent = ChatIntent(
            type=IntentType.ACTION_CALL,
            request_id="req-1",
            action_id="demo.broken",
        )
        result = engine.execute_intent(pid, intent)
        assert result.status == ExecutionStatus.FAILED
        assert "Handler error" in result.message

    def test_precondition_eval_error(self, setup):
        engine, registry, _, pid = setup
        
        action_bad_pre = ActionDeclaration(
            action_id="demo.badpre",
            title="Bad Pre",
            description="Bad",
            targets=["demo.counter"],
            input_schema={},
            preconditions=[
                ActionPrecondition(
                    id="check.bad",
                    description="Bad Syntax",
                    expr="1 / 0" # ZeroDivisionError
                )
            ],
            permission=ActionPermission(
                confirmation_required=False, risk=ActionRisk.LOW, visibility=ActionVisibility.USER
            )
        )
        registry.register_action(action_bad_pre, lambda i, s: ({}, [], "ok"))
        
        intent = ChatIntent(
            type=IntentType.ACTION_CALL,
            request_id="req-1",
            action_id="demo.badpre",
        )
        result = engine.execute_intent(pid, intent)
        assert result.status == ExecutionStatus.REJECTED
        assert "Error evaluating precondition" in result.message

    def test_execute_no_handler(self, setup):
        engine, registry, _, pid = setup
        # Register action manually in internal dict but skip handler registration
        # This is a bit of a hack but tests the engine's check
        action = ActionDeclaration(
            action_id="demo.nohandler",
            title="No Handler",
            description="Bad",
            targets=["demo.counter"],
            input_schema={},
            permission=ActionPermission(
                confirmation_required=False, risk=ActionRisk.LOW, visibility=ActionVisibility.USER
            )
        )
        registry._actions[action.action_id] = action
        # registry._handlers[action.action_id] remains empty
        
        intent = ChatIntent(
            type=IntentType.ACTION_CALL,
            request_id="req-1",
            action_id="demo.nohandler",
        )
        result = engine.execute_intent(pid, intent)
        assert result.status == ExecutionStatus.FAILED
        assert "No handler registered" in result.message

    def test_rate_limit(self, setup):
        engine, _, repo, pid = setup

        # Set rate limit to 2 per minute
        repo.set_project_limits(pid, {"limits": {"rate": {"per_minute": 2}}})

        intent = ChatIntent(
            type=IntentType.ACTION_CALL,
            request_id="req-1",
            action_id="demo.counter.set",
            inputs={"value": 1},
        )

        # 1st call: Success
        res1 = engine.execute_intent(pid, intent)
        assert res1.status == ExecutionStatus.SUCCESS

        # 2nd call: Success
        res2 = engine.execute_intent(pid, intent)
        assert res2.status == ExecutionStatus.SUCCESS

        # 3rd call: Should fail
        res3 = engine.execute_intent(pid, intent)
        assert res3.status == ExecutionStatus.REJECTED
        assert "Rate limit exceeded" in res3.message

    def test_engine_lock_direct(self, setup):
        engine, _, _, pid = setup
        # Call direct to ensure coverage
        lock = engine._get_project_lock(pid)
        assert lock is not None
        # Call again to hit the "if project_id in self.project_locks" branch (implicit in get)
        lock2 = engine._get_project_lock(pid)
        assert lock == lock2

    def test_engine_lock_reuse(self, setup):
        engine, _, _, pid = setup
        # First call creates the lock
        lock1 = engine._get_project_lock(pid)
        # Second call reuses it - explicitly hitting the cached branch
        lock2 = engine._get_project_lock(pid)
        assert lock1 is lock2
        assert pid in engine.project_locks

    def test_execute_plan_step_failure(self, setup):
        engine, _, _, pid = setup
        
        # Plan with 2 steps: 1st fails, 2nd should be skipped
        plan = ExecutionPlan(
            plan_id="p1",
            steps=[
                ChatIntent(
                    type=IntentType.ACTION_CALL,
                    request_id="r1",
                    action_id="missing.action" # Will reject
                ),
                ChatIntent(
                    type=IntentType.ACTION_CALL,
                    request_id="r2",
                    action_id="demo.counter.set",
                    inputs={"value": 10}
                )
            ]
        )
        
        results = engine.execute_plan(pid, plan)
        
        # Should have broken after first failure
        assert len(results) == 1
        assert results[0].status == ExecutionStatus.REJECTED

    def test_revert_with_no_history(self, setup):
        engine, _, repo, pid = setup
        
        # Create a snapshot in a DIFFERENT project so it exists in repo
        other_pid = "other-proj"
        snap = StateSnapshot(snapshot_id="s1", components={"comp": {"foo": "bar"}})
        repo.save_snapshot(other_pid, snap)
        
        # Revert 'pid' (which has no history) to 's1'
        # This triggers "if not current_snapshot:" branch
        result = engine.revert_to_snapshot(pid, "s1")
        
        assert result.status == ExecutionStatus.SUCCESS
        # Verify state
        latest = repo.get_latest_snapshot(pid)
        assert latest.components == {"comp": {"foo": "bar"}}

    def test_execute_plan_limits(self, setup):
        engine, _, _, pid = setup
        
        # Interactive mode: max 1 step
        plan_interactive = ExecutionPlan(plan_id="p1", steps=[
            ChatIntent(type=IntentType.ACTION_CALL, request_id="1", action_id="a", execution_mode=ExecutionMode.INTERACTIVE),
            ChatIntent(type=IntentType.ACTION_CALL, request_id="2", action_id="a", execution_mode=ExecutionMode.INTERACTIVE)
        ])
        res = engine.execute_plan(pid, plan_interactive)
        assert len(res) == 1
        assert res[0].error.code == "plan_limit_exceeded"

        # Autonomous mode: max 10 steps
        steps = [ChatIntent(type=IntentType.ACTION_CALL, request_id=str(i), action_id="a", execution_mode=ExecutionMode.AUTONOMOUS) for i in range(11)]
        plan_auto = ExecutionPlan(plan_id="p2", steps=steps)
        res = engine.execute_plan(pid, plan_auto)
        assert len(res) == 1
        assert res[0].error.code == "plan_limit_exceeded"

    def test_chained_simulation(self, setup):
        engine, registry, repo, pid = setup
        
        # Register an increment action
        action = ActionDeclaration(
            action_id="inc", title="Inc", description="Inc", targets=["c"],
            input_schema={"type": "object", "properties": {"v": {"type": "integer"}}},
            permission=ActionPermission(confirmation_required=False, risk=ActionRisk.LOW, visibility=ActionVisibility.USER)
        )
        def handler(inputs, snapshot):
            val = snapshot.components.get("c", {}).get("v", 0)
            new_val = val + inputs.get("v", 1)
            return {"c": {"v": new_val}}, [], "ok"
        registry.register_action(action, handler)

        plan = ExecutionPlan(plan_id="p1", steps=[
            ChatIntent(type=IntentType.ACTION_CALL, request_id="1", action_id="inc", inputs={"v": 10}, execution_mode=ExecutionMode.ASSISTED),
            ChatIntent(type=IntentType.ACTION_CALL, request_id="2", action_id="inc", inputs={"v": 5}, execution_mode=ExecutionMode.ASSISTED)
        ])

        # Execute with simulate=True
        results = engine.execute_plan(pid, plan, simulate=True)
        assert len(results) == 2
        assert results[0].simulated is True
        assert results[1].simulated is True
        
        # Check chaining: step 2 should have seen 10 and added 5 = 15
        assert results[1]._simulated_state["c"]["v"] == 15
        
        # Verify repository is still empty
        assert repo.get_latest_snapshot(pid) is None

    def test_memory_actions(self, setup):
        engine, _, repo, pid = setup
        uid = "user1"

        # 1. Missing user_id
        intent_rem = ChatIntent(type=IntentType.ACTION_CALL, request_id="1", action_id="memory.remember", inputs={"key": "k", "value": "v"})
        res = engine.execute_intent(pid, intent_rem)
        assert res.status == ExecutionStatus.REJECTED
        assert "User ID required" in res.message

        # 2. Simulation
        res = engine.execute_intent(pid, intent_rem, user_id=uid, simulate=True)
        assert res.status == ExecutionStatus.SUCCESS
        assert res.simulated is True
        assert repo.get_session_facts(pid, uid) == {}

        # 3. Real Remember
        res = engine.execute_intent(pid, intent_rem, user_id=uid)
        assert res.status == ExecutionStatus.SUCCESS
        assert repo.get_session_facts(pid, uid) == {"k": "v"}

        # 4. Real Forget
        intent_forg = ChatIntent(type=IntentType.ACTION_CALL, request_id="2", action_id="memory.forget", inputs={"key": "k"})
        res = engine.execute_intent(pid, intent_forg, user_id=uid)
        assert res.status == ExecutionStatus.SUCCESS
        assert repo.get_session_facts(pid, uid) == {}

        # 5. Memory error
        repo.save_session_fact = MagicMock(side_effect=Exception("DB Error"))
        res = engine.execute_intent(pid, intent_rem, user_id=uid)
        assert res.status == ExecutionStatus.FAILED
        assert "Memory error" in res.message

    def test_execute_intent_with_media_hashing(self, setup):
        engine, registry, repo, pid = setup
        
        action = ActionDeclaration(
            action_id="act", title="T", description="D", targets=["c"],
            input_schema={},
            permission=ActionPermission(confirmation_required=False, risk=ActionRisk.LOW, visibility=ActionVisibility.USER)
        )
        registry.register_action(action, lambda i, s: ({}, [], "ok"))
        
        media = IntentMedia(type="image", data="some-base64-data", mime_type="image/png")
        intent = ChatIntent(type=IntentType.ACTION_CALL, request_id="1", action_id="act", media=media)
        
        res = engine.execute_intent(pid, intent)
        assert res.status == ExecutionStatus.SUCCESS
        assert "media_hash" in res.metadata
        assert res.metadata["media_type"] == "image"


class TestEngineExceptions:
    @pytest.fixture
    def setup(self):
        registry = InMemoryRegistry()
        repository = InMemoryStateRepository()
        engine = ExecutionEngine(registry, repository)
        return engine, registry, repository

    def test_rejection_persistence_error(self, setup):
        """Test that a DB error during rejection logging doesn't crash the response."""
        engine, _, repository = setup
        pid = "proj-err"

        # Mock save_execution to raise an error
        original_save = repository.save_execution
        def breaking_save(project_id, result):
            raise ValueError("DB Crash")
        repository.save_execution = breaking_save

        intent = ChatIntent(
            type=IntentType.ACTION_CALL,
            request_id="req-1",
            action_id="missing.action",
        )
        
        # Should return REJECTED, not raise ValueError
        result = engine.execute_intent(pid, intent)
        assert result.status == ExecutionStatus.REJECTED
        assert "not found" in result.message

        # Restore
        repository.save_execution = original_save

    def test_failure_persistence_error(self, setup):
        """Test that a DB error during failure logging doesn't crash the response."""
        engine, registry, repository = setup
        pid = "proj-err"
        
        # Register action but no handler (triggers failure)
        action = ActionDeclaration(
            action_id="demo.nohandler",
            title="No Handler",
            description="Bad",
            targets=["demo"],
            input_schema={},
            permission=ActionPermission(
                confirmation_required=False, risk=ActionRisk.LOW, visibility=ActionVisibility.USER
            )
        )
        registry._actions[action.action_id] = action

        # Mock save_execution to raise an error
        original_save = repository.save_execution
        def breaking_save(project_id, result):
            raise ValueError("DB Crash")
        repository.save_execution = breaking_save

        intent = ChatIntent(
            type=IntentType.ACTION_CALL,
            request_id="req-1",
            action_id="demo.nohandler",
        )
        
        # Should return FAILED, not raise ValueError
        result = engine.execute_intent(pid, intent)
        assert result.status == ExecutionStatus.FAILED
        assert "No handler registered" in result.message

        # Restore
        repository.save_execution = original_save


