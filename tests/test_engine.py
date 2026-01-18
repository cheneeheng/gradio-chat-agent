import uuid
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from gradio_chat_agent.execution.engine import ExecutionEngine
from gradio_chat_agent.models.action import (
    ActionDeclaration,
    ActionPermission,
    ActionPrecondition,
    ActionRisk,
    ActionVisibility,
)
from gradio_chat_agent.models.component import (
    ComponentDeclaration,
    ComponentPermissions,
    ComponentInvariant,
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

        result = engine.execute_intent(pid, intent, user_roles=["admin"])
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
        result = engine.execute_intent(pid, intent, user_roles=["admin"])
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
        result = engine.execute_intent(pid, intent, user_roles=["admin"])
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
        
        result = engine.execute_intent(pid, intent, user_roles=["admin"])
        assert result.status == ExecutionStatus.REJECTED
        assert "Precondition failed" in result.message

        # Set state to 10
        repo.save_snapshot(pid, StateSnapshot(snapshot_id="1", components={"demo.counter": {"value": 10}}))
        
        result = engine.execute_intent(pid, intent, user_roles=["admin"])
        assert result.status == ExecutionStatus.SUCCESS

    def test_execute_invalid_intent_type(self, setup):
        engine, _, _, pid = setup
        intent = ChatIntent(
            type=IntentType.CLARIFICATION_REQUEST,
            request_id="req-1",
            question="What?"
        )
        result = engine.execute_intent(pid, intent, user_roles=["admin"])
        assert result.status == ExecutionStatus.REJECTED
        assert "only executes action_call" in result.message

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
        result = engine.execute_intent(pid, intent, user_roles=["admin"])
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
        result = engine.execute_intent(pid, intent, user_roles=["admin"])
        assert result.status == ExecutionStatus.REJECTED
        assert "Error evaluating precondition" in result.message

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
        res1 = engine.execute_intent(pid, intent, user_roles=["admin"])
        assert res1.status == ExecutionStatus.SUCCESS

        # 2nd call: Success
        res2 = engine.execute_intent(pid, intent, user_roles=["admin"])
        assert res2.status == ExecutionStatus.SUCCESS

        # 3rd call: Should fail
        res3 = engine.execute_intent(pid, intent, user_roles=["admin"])
        assert res3.status == ExecutionStatus.REJECTED
        assert "Rate limit exceeded" in res3.message

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
        
        results = engine.execute_plan(pid, plan, user_roles=["admin"])
        
        # Should have broken after first failure
        assert len(results) == 1
        assert results[0].status == ExecutionStatus.REJECTED

    def test_revert_to_snapshot(self, setup):
        engine, _, repo, pid = setup
        
        # Create a snapshot in a DIFFERENT project so it exists in repo
        other_pid = "other-proj"
        snap = StateSnapshot(snapshot_id="s1", components={"comp": {"foo": "bar"}})
        repo.save_snapshot(other_pid, snap)
        
        # Revert 'pid' (which has no history) to 's1'
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
        res = engine.execute_plan(pid, plan_interactive, user_roles=["admin"])
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
        results = engine.execute_plan(pid, plan, simulate=True, user_roles=["admin"])
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

        # Remember
        intent_rem = ChatIntent(type=IntentType.ACTION_CALL, request_id="1", action_id="memory.remember", inputs={"key": "k", "value": "v"})
        res = engine.execute_intent(pid, intent_rem, user_id=uid)
        assert res.status == ExecutionStatus.SUCCESS
        assert repo.get_session_facts(pid, uid) == {"k": "v"}

        # Forget
        intent_forg = ChatIntent(type=IntentType.ACTION_CALL, request_id="2", action_id="memory.forget", inputs={"key": "k"})
        res = engine.execute_intent(pid, intent_forg, user_id=uid)
        assert res.status == ExecutionStatus.SUCCESS
        assert repo.get_session_facts(pid, uid) == {}

    def test_budget_enforcement(self, setup):
        engine, registry, repo, pid = setup
        registry.register_action(
            ActionDeclaration(
                action_id="test.expensive", title="E", description="E", targets=["t"], 
                input_schema={}, permission=ActionPermission(confirmation_required=False, risk=ActionRisk.LOW, visibility=ActionVisibility.USER),
                cost=10.0
            ),
            handler=lambda i, s: (s.components, [], "Done")
        )
        repo.set_project_limits(pid, {"limits": {"budget": {"daily": 5}}})
        
        res = engine.execute_intent(pid, ChatIntent(type=IntentType.ACTION_CALL, request_id="r1", action_id="test.expensive"), user_roles=["admin"])
        assert res.status == ExecutionStatus.REJECTED
        assert res.error.code == "budget_exceeded"

    def test_invariant_enforcement(self, setup):
        engine, registry, repo, pid = setup
        registry.register_component(
            ComponentDeclaration(
                component_id="test.comp", title="C", description="C", state_schema={},
                permissions=ComponentPermissions(readable=True),
                invariants=[ComponentInvariant(description="P", expr="state['test.comp']['v'] >= 0")]
            )
        )
        registry.register_action(
            ActionDeclaration(
                action_id="test.set", title="S", description="S", targets=["test.comp"], 
                input_schema={}, permission=ActionPermission(confirmation_required=False, risk=ActionRisk.LOW, visibility=ActionVisibility.USER)
            ),
            handler=lambda i, s: ({"test.comp": {"v": i["v"]}}, [], "Set")
        )
        
        res = engine.execute_intent(pid, ChatIntent(type=IntentType.ACTION_CALL, request_id="r1", action_id="test.set", inputs={"v": -1}), user_roles=["admin"])
        assert res.status == ExecutionStatus.FAILED
        assert res.error.code == "invariant_violation"

    def test_execution_windows(self, setup):
        engine, _, repo, pid = setup
        repo.set_project_limits(pid, {"execution_windows": {"allowed": [{"days": ["never"], "hours": ["00:00", "23:59"]}]}})
        
        res = engine.execute_intent(pid, ChatIntent(type=IntentType.ACTION_CALL, request_id="r1", action_id="demo.counter.set", inputs={"value": 1}), user_roles=["admin"])
        assert res.status == ExecutionStatus.REJECTED
        assert res.error.code == "execution_window_violation"

    def test_approval_workflow(self, setup):
        engine, registry, repo, pid = setup
        repo.set_project_limits(pid, {"approvals": [{"min_cost": 5.0, "required_role": "admin"}]})
        registry.register_action(
            ActionDeclaration(
                action_id="test.exp", title="E", description="E", targets=["t"], input_schema={},
                permission=ActionPermission(confirmation_required=False, risk=ActionRisk.LOW, visibility=ActionVisibility.USER),
                cost=10.0
            ),
            handler=lambda i, s: (s.components, [], "ok")
        )
        
        res = engine.execute_intent(pid, ChatIntent(type=IntentType.ACTION_CALL, request_id="r1", action_id="test.exp"), user_roles=["operator"])
        assert res.status == ExecutionStatus.PENDING_APPROVAL

    def test_engine_db_failures(self, setup):
        engine, _, repo, pid = setup
        repo.save_execution = MagicMock(side_effect=Exception("DB Error"))
        
        # Rejection path
        res = engine.execute_intent(pid, ChatIntent(type=IntentType.ACTION_CALL, request_id="1", action_id="missing"), user_roles=["admin"])
        assert res.status == ExecutionStatus.REJECTED

        # Failure path
        res = engine._create_failure(pid, ChatIntent(type=IntentType.ACTION_CALL, request_id="2", action_id="a"), "fail")
        assert res.status == ExecutionStatus.FAILED

    def test_engine_safe_eval_all_nodes(self, setup):
        engine, _, _, _ = setup
        context = {"a": 1, "b": {"c": 2}, "d": [10, 20]}
        # Test various AST nodes allowed
        assert engine._safe_eval("a + 5", context) == 6
        assert engine._safe_eval("b['c'] == 2", context) is True
        assert engine._safe_eval("d[0] < d[1]", context) is True
        assert engine._safe_eval("-a == -1", context) is True
        assert engine._safe_eval("a is not None", context) is True
        assert engine._safe_eval("10 in d", context) is True
        assert engine._safe_eval("30 not in d", context) is True
        assert engine._safe_eval("True and (False or True)", context) is True

    def test_engine_safe_eval_forbidden_call(self, setup):
        engine, _, _, _ = setup
        with pytest.raises(ValueError, match="Forbidden expression node: Call"):
            engine._safe_eval("len(d)", {"d": [1]})

    def test_hourly_rate_limit(self, setup):
        engine, _, repo, pid = setup
        # Set hourly rate limit to 1 per hour
        repo.set_project_limits(pid, {"limits": {"rate": {"per_hour": 1}}})
        
        intent = ChatIntent(type=IntentType.ACTION_CALL, request_id="r1", action_id="demo.counter.set", inputs={"value": 1})
        
        # 1st call: Success
        assert engine.execute_intent(pid, intent, user_roles=["admin"]).status == ExecutionStatus.SUCCESS
        
        # 2nd call: Should fail (hourly)
        res = engine.execute_intent(pid, intent, user_roles=["admin"])
        assert res.status == ExecutionStatus.REJECTED
        assert "Hourly rate limit exceeded" in res.message

    def test_invariant_violation_error(self, setup):
        engine, registry, repo, pid = setup
        registry.register_component(
            ComponentDeclaration(
                component_id="bad.comp", title="B", description="B", state_schema={},
                permissions=ComponentPermissions(readable=True),
                invariants=[ComponentInvariant(description="Fail", expr="1 / 0")] # Division by zero
            )
        )
        intent = ChatIntent(type=IntentType.ACTION_CALL, request_id="r1", action_id="demo.counter.set", inputs={"value": 1})
        res = engine.execute_intent(pid, intent, user_roles=["admin"])
        assert res.status == ExecutionStatus.FAILED
        assert res.error.code == "invariant_error"

    def test_create_rejection_db_error(self, setup):
        engine, _, repo, pid = setup
        with patch.object(repo, 'save_execution', side_effect=Exception("DB Error")):
            intent = ChatIntent(type=IntentType.ACTION_CALL, request_id="r1", action_id="missing")
            # Should not crash
            res = engine.execute_intent(pid, intent, user_roles=["admin"])
            assert res.status == ExecutionStatus.REJECTED

    def test_create_failure_db_error(self, setup):
        engine, _, repo, pid = setup
        with patch.object(repo, 'save_execution', side_effect=Exception("DB Error")):
            intent = ChatIntent(type=IntentType.ACTION_CALL, request_id="r1", action_id="demo.counter.set", inputs={"value": 1})
            # Force a handler failure by mocking the handler ITSELF
            mock_handler = MagicMock(side_effect=Exception("Handler Fail"))
            with patch.object(engine.registry, 'get_handler', return_value=mock_handler):
                res = engine.execute_intent(pid, intent, user_roles=["admin"])
                assert res.status == ExecutionStatus.FAILED

    def test_revert_to_snapshot_missing_current(self, setup):
        engine, _, repo, pid = setup
        # Create a snapshot to revert to
        repo.save_snapshot("other", StateSnapshot(snapshot_id="target", components={"a": {"v": 1}}))
        
        # Ensure repository returns None for latest snapshot
        with patch.object(repo, 'get_latest_snapshot', return_value=None):
            res = engine.revert_to_snapshot(pid, "target")
            assert res.status == ExecutionStatus.SUCCESS
            assert "target" in res.message

    def test_revert_to_snapshot_not_found(self, setup):
        engine, _, _, pid = setup
        res = engine.revert_to_snapshot(pid, "nonexistent")
        assert res.status == ExecutionStatus.FAILED
        assert res.error.code == "not_found"

    def test_execute_plan_autonomous_limit(self, setup):
        engine, _, _, pid = setup
        # Autonomous mode: max 10 steps
        steps = [ChatIntent(type=IntentType.ACTION_CALL, request_id=str(i), action_id="a", execution_mode=ExecutionMode.AUTONOMOUS) for i in range(11)]
        plan_auto = ExecutionPlan(plan_id="p2", steps=steps)
        res = engine.execute_plan(pid, plan_auto, user_roles=["admin"])
        assert len(res) == 1
        assert res[0].error.code == "plan_limit_exceeded"

    def test_execute_project_archived(self, setup):
        engine, _, repo, pid = setup
        repo.create_project(pid, "P1")
        repo.archive_project(pid)
        intent = ChatIntent(type=IntentType.ACTION_CALL, request_id="r1", action_id="demo.counter.set", inputs={"value": 1})
        res = engine.execute_intent(pid, intent, user_roles=["admin"])
        assert res.status == ExecutionStatus.REJECTED
        assert res.error.code == "project_archived"

    def test_memory_actions_error(self, setup):
        engine, _, repo, pid = setup
        intent = ChatIntent(type=IntentType.ACTION_CALL, request_id="1", action_id="memory.remember", inputs={"key": "k", "value": "v"})
        with patch.object(repo, 'save_session_fact', side_effect=Exception("Disk Full")):
            res = engine.execute_intent(pid, intent, user_id="u1")
            assert res.status == ExecutionStatus.FAILED
            assert "Memory error" in res.message

    def test_invariant_eval_error(self, setup):
        engine, registry, repo, pid = setup
        registry.register_component(
            ComponentDeclaration(
                component_id="bad.comp", title="B", description="B", state_schema={},
                permissions=ComponentPermissions(readable=True),
                invariants=[ComponentInvariant(description="Fail", expr="state['missing']['key']")] # KeyError
            )
        )
        intent = ChatIntent(type=IntentType.ACTION_CALL, request_id="r1", action_id="demo.counter.set", inputs={"value": 1})
        res = engine.execute_intent(pid, intent, user_roles=["admin"])
        assert res.status == ExecutionStatus.FAILED
        assert res.error.code == "invariant_error"

    def test_execute_missing_action_id_intent(self, setup):
        engine, _, _, pid = setup
        intent = ChatIntent(type=IntentType.ACTION_CALL, request_id="r1")
        res = engine.execute_intent(pid, intent, user_roles=["admin"])
        assert res.status == ExecutionStatus.REJECTED
        assert "Missing action_id" in res.message

    def test_memory_actions_validation(self, setup):
        engine, _, repo, pid = setup
        # Missing user_id
        intent = ChatIntent(type=IntentType.ACTION_CALL, request_id="1", action_id="memory.remember", inputs={"key": "k", "value": "v"})
        res = engine.execute_intent(pid, intent, user_roles=["admin"])
        assert res.status == ExecutionStatus.REJECTED
        assert "User ID required" in res.message

        # Simulation
        res = engine.execute_intent(pid, intent, user_id="u1", simulate=True, user_roles=["admin"])
        assert res.status == ExecutionStatus.SUCCESS
        assert res.simulated is True

    def test_no_handler_failure(self, setup):
        engine, registry, _, pid = setup
        # Register action without handler manually
        action = ActionDeclaration(
            action_id="no.handler", title="N", description="N", targets=["demo.counter"],
            input_schema={}, permission=ActionPermission(confirmation_required=False, risk=ActionRisk.LOW, visibility=ActionVisibility.USER)
        )
        registry._actions["no.handler"] = action
        intent = ChatIntent(type=IntentType.ACTION_CALL, request_id="r1", action_id="no.handler")
        res = engine.execute_intent(pid, intent, user_roles=["admin"])
        assert res.status == ExecutionStatus.FAILED
        assert "No handler registered" in res.message

    def test_media_hashing(self, setup):
        engine, _, _, pid = setup
        media = IntentMedia(type="image", data="some-data", mime_type="image/png")
        intent = ChatIntent(type=IntentType.ACTION_CALL, request_id="r1", action_id="demo.counter.set", inputs={"value": 1}, media=media)
        res = engine.execute_intent(pid, intent, user_roles=["admin"])
        assert res.status == ExecutionStatus.SUCCESS
        assert "media_hash" in res.metadata
        assert res.metadata["media_type"] == "image"

    def test_execution_window_match(self, setup):
        engine, _, _, _ = setup
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc)
        day = now.strftime("%a").lower()
        # Create a window that matches current time
        windows = [{"days": [day], "hours": ["00:00", "23:59"]}]
        assert engine._is_within_execution_window(windows) is True
