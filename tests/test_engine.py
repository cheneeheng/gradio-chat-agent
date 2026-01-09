import uuid
from typing import Any

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
    ExecutionStatus,
    IntentType,
)
from gradio_chat_agent.models.intent import ChatIntent
from gradio_chat_agent.models.state_snapshot import StateSnapshot
from gradio_chat_agent.persistence.repository import InMemoryStateRepository
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


