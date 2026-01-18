import uuid
import hmac
import hashlib
import json
from unittest.mock import MagicMock
import pytest
from gradio_chat_agent.api.endpoints import ApiEndpoints
from gradio_chat_agent.execution.engine import ExecutionEngine
from gradio_chat_agent.persistence.in_memory import InMemoryStateRepository
from gradio_chat_agent.registry.in_memory import InMemoryRegistry
from gradio_chat_agent.models.action import ActionDeclaration, ActionPermission, ActionRisk, ActionVisibility
from gradio_chat_agent.models.component import (
    ComponentDeclaration,
    ComponentPermissions,
)
from gradio_chat_agent.models.enums import (
    ActionRisk,
    ActionVisibility,
    ExecutionMode,
    ExecutionStatus,
    ProjectOp,
    MembershipOp,
    WebhookOp,
    ScheduleOp,
)
from gradio_chat_agent.models.execution_result import ExecutionResult
from gradio_chat_agent.models.state_snapshot import StateSnapshot


class TestApiEndpoints:
    @pytest.fixture
    def setup(self):
        registry = InMemoryRegistry()
        repository = InMemoryStateRepository()
        engine = ExecutionEngine(registry, repository)
        api = ApiEndpoints(engine)
        project_id = "proj-1"

        # Register a dummy component
        comp = ComponentDeclaration(
            component_id="test.comp",
            title="Test Component",
            description="For testing",
            state_schema={
                "type": "object",
                "properties": {"val": {"type": "integer"}},
            },
            permissions=ComponentPermissions(readable=True),
        )
        registry.register_component(comp)

        # Register a dummy action
        action = ActionDeclaration(
            action_id="test.action",
            title="Test Action",
            description="Does something",
            targets=["test.comp"],
            input_schema={
                "type": "object",
                "properties": {"val": {"type": "integer"}},
            },
            permission=ActionPermission(
                confirmation_required=False,
                risk=ActionRisk.LOW,
                visibility=ActionVisibility.USER,
            ),
        )

        def handler(inputs, snapshot):
            new_comps = snapshot.components.copy()
            new_comps["test.comp"] = {"val": inputs.get("val", 0)}
            return new_comps, [], "Action executed"

        registry.register_action(action, handler)

        return api, engine, repository, project_id

    def test_execute_action_success(self, setup):
        api, _, repo, pid = setup

        # Initial state
        repo.save_snapshot(
            pid,
            StateSnapshot(
                snapshot_id="0", components={"test.comp": {"val": 0}}
            ),
        )

        result = api.execute_action(
            project_id=pid,
            action_id="test.action",
            inputs={"val": 42},
            mode="assisted",
        )

        assert result["code"] == 0
        assert result["message"] == "Action executed"
        assert result["data"]["status"] == ExecutionStatus.SUCCESS

        # Verify persistence
        history = repo.get_execution_history(pid)
        assert len(history) == 1
        assert history[0].status == ExecutionStatus.SUCCESS

    def test_simulate_action_success(self, setup):
        api, _, repo, pid = setup
        repo.save_snapshot(pid, StateSnapshot(snapshot_id="0", components={"test.comp": {"val": 0}}))

        result = api.simulate_action(
            project_id=pid,
            action_id="test.action",
            inputs={"val": 42},
        )

        assert result["code"] == 0
        assert result["data"]["simulated"] is True
        
        # Verify NO persistence
        history = repo.get_execution_history(pid)
        assert len(history) == 0

    def test_execute_action_failure_validation(self, setup):
        api, _, _, pid = setup

        # Invalid inputs (string instead of int)
        result = api.execute_action(
            project_id=pid,
            action_id="test.action",
            inputs={"val": "not-an-int"},
            mode="assisted",
        )

        assert result["code"] == 1
        assert "Input validation failed" in result["message"]

    def test_execute_plan_success(self, setup):
        api, _, repo, pid = setup

        repo.save_snapshot(
            pid,
            StateSnapshot(
                snapshot_id="0", components={"test.comp": {"val": 0}}
            ),
        )

        plan = {
            "plan_id": "plan-1",
            "steps": [
                {
                    "type": "action_call",
                    "request_id": str(uuid.uuid4()),
                    "action_id": "test.action",
                    "inputs": {"val": 10},
                    "timestamp": "2023-01-01T00:00:00Z",
                },
                {
                    "type": "action_call",
                    "request_id": str(uuid.uuid4()),
                    "action_id": "test.action",
                    "inputs": {"val": 20},
                    "timestamp": "2023-01-01T00:00:00Z",
                },
            ],
        }

        result = api.execute_plan(project_id=pid, plan=plan)

        assert result["code"] == 0
        results = result["data"]
        assert len(results) == 2
        assert results[0]["status"] == ExecutionStatus.SUCCESS
        assert results[1]["status"] == ExecutionStatus.SUCCESS

        # Verify final state
        snapshot = repo.get_latest_snapshot(pid)
        assert snapshot.components["test.comp"]["val"] == 20

    def test_simulate_plan_success(self, setup):
        api, _, repo, pid = setup
        repo.save_snapshot(pid, StateSnapshot(snapshot_id="0", components={"test.comp": {"val": 0}}))

        plan = {
            "plan_id": "plan-1",
            "steps": [
                {
                    "type": "action_call",
                    "request_id": str(uuid.uuid4()),
                    "action_id": "test.action",
                    "inputs": {"val": 10},
                    "timestamp": "2023-01-01T00:00:00Z",
                }
            ],
        }

        result = api.simulate_plan(project_id=pid, plan=plan)
        assert result["code"] == 0
        assert result["data"][0]["simulated"] is True
        
        # Verify NO persistence
        assert repo.get_latest_snapshot(pid).components["test.comp"]["val"] == 0

    def test_simulate_plan_invalid(self, setup):
        api, _, _, pid = setup
        res = api.simulate_plan(pid, {"invalid": "data"})
        assert res["code"] == 1
        assert "Invalid plan" in res["message"]

    def test_revert_snapshot(self, setup):
        api, _, repo, pid = setup

        # Create history
        repo.save_snapshot(
            pid,
            StateSnapshot(
                snapshot_id="snap-1", components={"test.comp": {"val": 10}}
            ),
        )
        repo.save_snapshot(
            pid,
            StateSnapshot(
                snapshot_id="snap-2", components={"test.comp": {"val": 20}}
            ),
        )

        # Revert to snap-1
        result = api.revert_snapshot(pid, "snap-1")

        assert result["code"] == 0
        assert "Reverted state to snapshot snap-1" in result["message"]

        # Verify current state matches snap-1
        latest = repo.get_latest_snapshot(pid)
        assert latest.components["test.comp"]["val"] == 10
        assert latest.snapshot_id != "snap-1"  # Should be a NEW snapshot ID

        # Verify audit log contains revert action
        history = repo.get_execution_history(pid)
        assert history[0].action_id == "system.revert"

    def test_webhook_execute_success(self, setup):
        api, _, repo, pid = setup

        # Inject webhook manually into in-memory repo
        webhook_id = "wh-1"
        secret = "super-secret"
        repo._webhooks[webhook_id] = {
            "id": webhook_id,
            "project_id": pid,
            "action_id": "test.action",
            "secret": secret,
            "inputs_template": {"val": "{{ value }}"},
            "enabled": True,
        }

        payload = {"value": 99}
        
        # Calculate correct HMAC signature
        import hmac
        import hashlib
        import json
        payload_bytes = json.dumps(payload, sort_keys=True).encode("utf-8")
        signature = hmac.new(
            secret.encode("utf-8"), payload_bytes, hashlib.sha256
        ).hexdigest()

        result = api.webhook_execute(webhook_id, payload, signature=signature)

        assert result["code"] == 0
        assert result["data"]["status"] == ExecutionStatus.SUCCESS

        # Verify state
        latest = repo.get_latest_snapshot(pid)
        assert latest.components["test.comp"]["val"] == 99

        # Verify audit log and trace
        history = repo.get_execution_history(pid)
        assert history[0].action_id == "test.action"

    def test_api_triggered_action_audit(self, setup):
        api, _, repo, pid = setup

        # Execute an action
        api.execute_action(pid, "test.action", {"val": 123}, mode="autonomous")

        # Verify audit log
        res = api.get_audit_log(pid)
        log = res["data"]
        assert len(log) == 1
        assert log[0]["action_id"] == "test.action"
        assert log[0]["status"] == ExecutionStatus.SUCCESS

    def test_webhook_execute_invalid_signature(self, setup):
        api, _, repo, pid = setup

        webhook_id = "wh-1"
        repo._webhooks[webhook_id] = {
            "id": webhook_id,
            "project_id": pid,
            "action_id": "test.action",
            "secret": "correct-secret",
            "inputs_template": None,
            "enabled": True,
        }

        result = api.webhook_execute(webhook_id, {}, signature="wrong-secret")
        assert result["code"] == 1
        assert "Invalid signature" in result["message"]

    def test_get_registry(self, setup):
        api, _, _, pid = setup

        res = api.get_registry(pid)
        assert res["code"] == 0
        reg_data = res["data"]

        assert "components" in reg_data
        assert "actions" in reg_data

        comp_ids = [c["component_id"] for c in reg_data["components"]]
        assert "test.comp" in comp_ids

        action_ids = [a["action_id"] for a in reg_data["actions"]]
        assert "test.action" in action_ids

    def test_get_audit_log(self, setup):
        api, _, repo, pid = setup

        # Create some history
        repo.save_snapshot(pid, StateSnapshot(snapshot_id="0", components={}))
        api.execute_action(pid, "test.action", {"val": 1})
        api.execute_action(pid, "test.action", {"val": 2})

        res = api.get_audit_log(pid, limit=10)
        assert res["code"] == 0
        log = res["data"]

        assert len(log) == 2
        assert log[0]["action_id"] == "test.action"
        assert log[0]["state_diff"][0]["value"] == 2

    def test_manage_project(self, setup):
        api, _, repo, _ = setup
        
        # Create
        res = api.manage_project(ProjectOp.CREATE, name="New Project", user_id="admin")
        assert res["code"] == 0
        new_pid = res["data"]["project_id"]
        assert new_pid in repo._projects
        assert repo._projects[new_pid]["name"] == "New Project"

        # Archive
        res = api.manage_project(ProjectOp.ARCHIVE, project_id=new_pid, user_id="admin")
        assert res["code"] == 0
        assert repo._projects[new_pid]["archived_at"] is not None

        # Purge
        res = api.manage_project(ProjectOp.PURGE, project_id=new_pid, user_id="admin", confirmed=True)
        assert res["code"] == 0
        assert new_pid not in repo._projects

    def test_manage_membership(self, setup):
        api, _, repo, pid = setup
        
        # Add
        res = api.manage_membership(MembershipOp.ADD, pid, "alice", "viewer")
        assert res["code"] == 0
        members = repo.get_project_members(pid)
        assert len(members) == 1
        assert members[0]["user_id"] == "alice"
        assert members[0]["role"] == "viewer"

        # Update
        res = api.manage_membership(MembershipOp.UPDATE_ROLE, pid, "alice", "admin")
        assert res["code"] == 0
        members = repo.get_project_members(pid)
        assert members[0]["role"] == "admin"

        # Remove
        res = api.manage_membership(MembershipOp.REMOVE, pid, "alice")
        assert res["code"] == 0
        members = repo.get_project_members(pid)
        assert len(members) == 0

    def test_manage_webhook(self, setup):
        api, _, repo, pid = setup
        
        config = {
            "project_id": pid,
            "action_id": "test.action",
            "secret": "s3cret",
            "enabled": True
        }

        # Create
        res = api.manage_webhook(WebhookOp.CREATE, config=config)
        assert res["code"] == 0
        wh_id = res["data"]["webhook_id"]
        assert wh_id in repo._webhooks

        # Update
        new_config = config.copy()
        new_config["secret"] = "new-secret"
        res = api.manage_webhook(WebhookOp.UPDATE, webhook_id=wh_id, config=new_config)
        assert res["code"] == 0
        assert repo._webhooks[wh_id]["secret"] == "new-secret"

        # Delete
        res = api.manage_webhook(WebhookOp.DELETE, webhook_id=wh_id)
        assert res["code"] == 0
        assert wh_id not in repo._webhooks

    def test_manage_schedule(self, setup):
        api, _, repo, pid = setup
        
        config = {
            "project_id": pid,
            "action_id": "test.action",
            "cron": "0 0 * * *",
            "inputs": {"val": 1},
            "enabled": True
        }

        # Create
        res = api.manage_schedule(ScheduleOp.CREATE, config=config)
        assert res["code"] == 0
        sch_id = res["data"]["schedule_id"]
        assert sch_id in repo._schedules

        # Update
        new_config = config.copy()
        new_config["cron"] = "0 12 * * *"
        res = api.manage_schedule(ScheduleOp.UPDATE, schedule_id=sch_id, config=new_config)
        assert res["code"] == 0
        assert repo._schedules[sch_id]["cron"] == "0 12 * * *"

        # Delete
        res = api.manage_schedule(ScheduleOp.DELETE, schedule_id=sch_id)
        assert res["code"] == 0
        assert sch_id not in repo._schedules

    def test_update_project_policy(self, setup):
        api, _, repo, pid = setup

        policy = {"limits": {"rate": {"per_minute": 5}}}

        res = api.update_project_policy(pid, policy)
        assert res["code"] == 0

        current_policy = repo.get_project_limits(pid)
        assert current_policy["limits"]["rate"]["per_minute"] == 5

    def test_manage_project_invalid(self, setup):
        api, _, _, pid = setup
        assert api.manage_project(ProjectOp.CREATE, name=None, user_id="admin")["code"] == 1
        assert api.manage_project(ProjectOp.ARCHIVE, project_id=None, user_id="admin")["code"] == 1
        assert api.manage_project(ProjectOp.PURGE, project_id=None, user_id="admin")["code"] == 1
        assert api.manage_project("unknown", user_id="admin")["code"] == 1

    def test_manage_membership_invalid(self, setup):
        api, _, _, pid = setup
        assert api.manage_membership(MembershipOp.ADD, pid, "u", role=None)["code"] == 1
        assert api.manage_membership(MembershipOp.UPDATE_ROLE, pid, "u", role=None)["code"] == 1
        assert api.manage_membership("unknown", pid, "u")["code"] == 1

    def test_manage_webhook_invalid(self, setup):
        api, _, _, pid = setup
        assert api.manage_webhook(WebhookOp.CREATE, config=None)["code"] == 1
        assert api.manage_webhook(WebhookOp.UPDATE, webhook_id=None, config=None)["code"] == 1
        assert api.manage_webhook(WebhookOp.DELETE, webhook_id=None)["code"] == 1
        assert api.manage_webhook("unknown")["code"] == 1

    def test_manage_schedule_invalid(self, setup):
        api, _, _, pid = setup
        assert api.manage_schedule(ScheduleOp.CREATE, config=None)["code"] == 1
        assert api.manage_schedule(ScheduleOp.UPDATE, schedule_id=None, config=None)["code"] == 1
        assert api.manage_schedule(ScheduleOp.DELETE, schedule_id=None)["code"] == 1
        assert api.manage_schedule("unknown")["code"] == 1

    def test_api_execute_action_none_inputs(self, setup):
        api, engine, repo, pid = setup
        # Mock engine to avoid full setup
        engine.execute_intent = MagicMock(return_value=ExecutionResult(
            request_id="1", action_id="a", status="success", state_snapshot_id="s", state_diff=[]
        ))
        
        # Call with inputs=None
        api.execute_action(pid, "test.action", inputs=None)
        
        # Verify call was made with empty dict
        args, kwargs = engine.execute_intent.call_args
        if 'intent' in kwargs:
            assert kwargs['intent'].inputs == {}
        else:
             assert args[1].inputs == {}

    def test_api_execute_plan_invalid(self, setup):
        api, _, _, pid = setup
        # Invalid plan dict
        res = api.execute_plan(pid, {"invalid": "data"})
        assert res["code"] == 1
        assert "Invalid plan" in res["message"]

    def test_webhook_edge_cases(self, setup):
        api, _, repo, pid = setup
        
        # Non-existent
        res = api.webhook_execute("missing", {}, "sig")
        assert res["code"] == 1
        assert "not found" in res["message"]
        
        # Disabled
        repo._webhooks["disabled"] = {"id": "disabled", "enabled": False}
        res = api.webhook_execute("disabled", {}, "sig")
        assert res["code"] == 1
        assert "disabled" in res["message"]
        
        # No template (pass through) & Static values
        repo._webhooks["passthrough"] = {
            "id": "passthrough", "enabled": True, "secret": "s",
            "project_id": pid, "action_id": "act", 
            "inputs_template": None
        }
        repo._webhooks["static"] = {
            "id": "static", "enabled": True, "secret": "s",
            "project_id": pid, "action_id": "act",
            "inputs_template": {"static": 123, "dynamic": "{{ val }}", "plain": "plain_text"}
        }
        
        # Mock execute_intent
        api.engine.execute_intent = MagicMock(return_value=ExecutionResult(
            request_id="1", action_id="a", status="success", state_snapshot_id="s", state_diff=[]
        ))
        
        # Test pass through
        payload_passthrough = {"foo": "bar"}
        payload_bytes = json.dumps(payload_passthrough, sort_keys=True).encode("utf-8")
        sig_passthrough = hmac.new(b"s", payload_bytes, hashlib.sha256).hexdigest()
        
        api.webhook_execute("passthrough", payload_passthrough, sig_passthrough)
        args, kwargs = api.engine.execute_intent.call_args
        if 'intent' in kwargs:
            assert kwargs['intent'].inputs == {"foo": "bar"}
        else:
            assert args[1].inputs == {"foo": "bar"}
        
        # Test static/dynamic mix - hitting the "else" branch for plain strings
        payload_static = {"val": 123}
        payload_bytes = json.dumps(payload_static, sort_keys=True).encode("utf-8")
        sig_static = hmac.new(b"s", payload_bytes, hashlib.sha256).hexdigest()
        
        api.webhook_execute("static", payload_static, sig_static)
        args, kwargs = api.engine.execute_intent.call_args
        inputs = kwargs['intent'].inputs if 'intent' in kwargs else args[1].inputs
        assert inputs == {"static": 123, "dynamic": 123, "plain": "plain_text"}

    def test_revert_invalid_snapshot(self, setup):
        api, _, _, pid = setup
        res = api.revert_snapshot(pid, "invalid_snap_id")
        assert res["code"] == 1
        assert "not found" in res["message"]

    def test_api_get_registry_filtering(self, setup):
        api, _, _, pid = setup
        api.engine.repository.add_project_member(pid, "u1", "viewer")
        
        api.engine.registry.register_action(
            ActionDeclaration(
                action_id="dev.a", title="D", description="D", targets=["t"], 
                input_schema={},
                permission=ActionPermission(confirmation_required=False, risk=ActionRisk.LOW, visibility=ActionVisibility.DEVELOPER)
            ),
            handler=lambda i, s: ({}, [], "D")
        )
        
        res = api.get_registry(pid, user_id="u1")
        reg = res["data"]
        action_ids = [a["action_id"] for a in reg["actions"]]
        assert "dev.a" not in action_ids

    def test_api_manage_webhook_delete_missing_id(self, setup):
        api, _, _, _ = setup
        res = api.manage_webhook(WebhookOp.DELETE, webhook_id=None)
        assert res["code"] == 1
        assert "Webhook ID required" in res["message"]

    def test_api_manage_schedule_delete_missing_id(self, setup):
        api, _, _, _ = setup
        res = api.manage_schedule(ScheduleOp.DELETE, schedule_id=None)
        assert res["code"] == 1
        assert "Schedule ID required" in res["message"]

    def test_execute_action_empty_mode(self, setup):
        api, engine, _, pid = setup
        engine.execute_intent = MagicMock(return_value=MagicMock(status="success", message="OK", model_dump=lambda **k: {}))
        
        api.execute_action(pid, "act", {}, mode="")
        
        args, kwargs = engine.execute_intent.call_args
        assert kwargs["intent"].execution_mode == ExecutionMode.ASSISTED

    def test_webhook_template_conversions(self, setup):
        api, _, repo, pid = setup
        webhook_id = "wh-conv"
        repo._webhooks[webhook_id] = {
            "id": webhook_id, "project_id": pid, "action_id": "act", "secret": "s", "enabled": True,
            "inputs_template": {
                "b_true": "{{ t }}", "b_false": "{{ f }}", 
                "i_val": "{{ i }}", "f_val": "{{ fl }}",
                "s_val": "{{ s }}"
            }
        }
        
        payload = {"t": "true", "f": "false", "i": "123", "fl": "12.34", "s": "hello"}
        
        # Mock HMAC
        import hmac, hashlib, json
        payload_bytes = json.dumps(payload, sort_keys=True).encode("utf-8")
        sig = hmac.new(b"s", payload_bytes, hashlib.sha256).hexdigest()
        
        # Mock execute
        api.engine.execute_intent = MagicMock(return_value=MagicMock(status="success", message="OK", model_dump=lambda **k: {}))
        
        api.webhook_execute(webhook_id, payload, sig)
        
        args, kwargs = api.engine.execute_intent.call_args
        inputs = kwargs["intent"].inputs
        assert inputs["b_true"] is True
        assert inputs["b_false"] is False
        assert inputs["i_val"] == 123
        assert inputs["f_val"] == 12.34
        assert inputs["s_val"] == "hello"

    def test_webhook_template_error(self, setup):
        import hmac, hashlib
        api, _, repo, pid = setup
        webhook_id = "wh-err"
        repo._webhooks[webhook_id] = {
            "id": webhook_id, "project_id": pid, "action_id": "act", "secret": "s", "enabled": True,
            "inputs_template": {"val": "{{ 1/0 }}"} # ZeroDivisionError in jinja? No, Jinja handles it differently usually, but let's try syntax error
        }
        repo._webhooks[webhook_id]["inputs_template"] = {"val": "{{ x }"} # Syntax Error
        
        payload = {}
        payload_bytes = b"{}"
        sig = hmac.new(b"s", payload_bytes, hashlib.sha256).hexdigest()
        
        res = api.webhook_execute(webhook_id, payload, sig)
        assert res["code"] == 1
        assert "Template rendering error" in res["message"]

    def test_list_users_string_date(self, setup):
        api, _, repo, _ = setup
        repo._users["u1"] = {"id": "u1", "created_at": "2023-01-01T00:00:00"}
        
        res = api.list_users(user_id="admin")
        assert res["data"][0]["created_at"] == "2023-01-01T00:00:00"

    def test_delete_user_permission_denied(self, setup):
        api, _, _, _ = setup
        res = api.delete_user("u1", user_id="viewer")
        assert res["code"] == 1
        assert "Permission denied" in res["message"]

    def test_simulate_action_none_inputs(self, setup):
        api, engine, _, pid = setup
        engine.execute_intent = MagicMock(return_value=MagicMock(status="success", message="OK", model_dump=lambda **k: {}))
        api.simulate_action(pid, "act", None)
        args, kwargs = engine.execute_intent.call_args
        assert kwargs["intent"].inputs == {}

    def test_manage_project_edge_cases(self, setup):
        api, _, _, _ = setup
        
        # Not admin
        res = api.manage_project(ProjectOp.CREATE, name="p", user_id="user")
        assert res["code"] == 1
        assert "Permission denied" in res["message"]
        
        # Archive missing project_id
        res = api.manage_project(ProjectOp.ARCHIVE, project_id=None, user_id="admin")
        assert res["code"] == 1
        assert "Project ID required" in res["message"]
        
        # Purge missing project_id
        res = api.manage_project(ProjectOp.PURGE, project_id=None, user_id="admin")
        assert res["code"] == 1
        assert "Project ID required" in res["message"]
        
        # Unknown op
        # We need to bypass the Enum type check if using python enum, but the method type hint says ProjectOp.
        # However, passing a string that isn't in Enum might fail Pydantic validation if strictly typed, 
        # but here it's a method argument. 
        # If I pass a string "unknown", it won't equal any ProjectOp member.
        res = api.manage_project("unknown", user_id="admin")
        assert res["code"] == 1
        assert "Unknown operation" in res["message"]

    def test_budget_forecast(self, setup):
        api, _, _, pid = setup
        # Just check it calls the service and returns data
        res = api.budget_forecast(pid)
        assert "status" in res["data"]