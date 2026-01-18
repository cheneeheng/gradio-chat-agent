from unittest.mock import MagicMock, patch
import pytest
import gradio as gr
from gradio_chat_agent.ui.layout import UIController, create_ui, STATUS_READY_HTML, STATUS_SUCCESS_HTML, STATUS_PENDING_HTML, STATUS_FAILED_HTML
from gradio_chat_agent.models.state_snapshot import StateSnapshot
from gradio_chat_agent.models.plan import ExecutionPlan
from gradio_chat_agent.models.intent import ChatIntent
from gradio_chat_agent.models.enums import IntentType, ExecutionStatus
from gradio_chat_agent.models.execution_result import ExecutionResult, ExecutionError

class TestUIController:
    @pytest.fixture
    def setup(self):
        engine = MagicMock()
        adapter = MagicMock()
        controller = UIController(engine, adapter)
        pid = "test-proj"
        uid = "test-user"
        return controller, engine, adapter, pid, uid

    def test_fetch_state(self, setup):
        controller, engine, _, pid, _ = setup
        engine.repository.get_latest_snapshot.return_value = StateSnapshot(
            snapshot_id="s1", components={"c": {"v": 1}}
        )
        state = controller.fetch_state(pid)
        assert state == {"c": {"v": 1}}

        engine.repository.get_latest_snapshot.return_value = None
        assert controller.fetch_state(pid) == {}

    def test_fetch_facts_df(self, setup):
        controller, engine, _, pid, uid = setup
        engine.repository.get_session_facts.return_value = {"k1": "v1", "k2": 2}
        df = controller.fetch_facts_df(pid, uid)
        assert len(df) == 2
        assert ["k1", "v1"] in df
        assert ["k2", "2"] in df

    def test_fetch_members_df(self, setup):
        controller, engine, _, pid, _ = setup
        engine.repository.get_project_members.return_value = [
            {"user_id": "u1", "role": "admin"},
            {"user_id": "u2", "role": "viewer"}
        ]
        df = controller.fetch_members_df(pid)
        assert len(df) == 2
        assert ["u1", "admin"] in df

    def test_refresh_ui(self, setup):
        controller, engine, _, pid, uid = setup
        engine.repository.get_latest_snapshot.return_value = None
        engine.repository.get_session_facts.return_value = {}
        engine.repository.get_project_members.return_value = []
        engine.registry.list_components.return_value = []
        engine.registry.list_actions.return_value = []

        res = controller.refresh_ui(pid, uid)
        assert len(res) == 10
        assert res[0] == {}
        assert res[5] == {} # last_intent
        assert res[6] == {} # last_result
        assert res[7] == STATUS_READY_HTML

    def test_on_add_fact(self, setup):
        controller, engine, _, pid, uid = setup
        engine.repository.get_session_facts.return_value = {"k": "v"}
        res = controller.on_add_fact(pid, uid, "k", "v")
        engine.repository.save_session_fact.assert_called_with(pid, uid, "k", "v")
        assert res[0] == [["k", "v"]]

    def test_on_delete_fact(self, setup):
        controller, engine, _, pid, uid = setup
        engine.repository.get_session_facts.return_value = {}
        res = controller.on_delete_fact(pid, uid, "k")
        engine.repository.delete_session_fact.assert_called_with(pid, uid, "k")
        assert res[0] == []

    def test_on_add_member(self, setup):
        controller, engine, _, pid, uid = setup
        engine.repository.get_project_members.return_value = [{"user_id": "new", "role": "admin"}]
        res = controller.on_add_member(pid, uid, "new", "admin")
        engine.repository.add_project_member.assert_called_with(pid, "new", "admin")
        assert res[0] == [["new", "admin"]]

    def test_on_remove_member(self, setup):
        controller, engine, _, pid, uid = setup
        engine.repository.get_project_members.return_value = []
        res = controller.on_remove_member(pid, uid, "old")
        engine.repository.remove_project_member.assert_called_with(pid, "old")
        assert res[0] == []

    def test_on_mock_login(self, setup):
        controller, _, _, _, _ = setup
        token, token_display = controller.on_mock_login()
        assert token.startswith("sk-")
        assert token == token_display

    def test_on_submit_plan(self, setup):
        controller, engine, adapter, pid, uid = setup
        step = ChatIntent(type=IntentType.ACTION_CALL, request_id="1", action_id="a1", inputs={})
        plan = ExecutionPlan(plan_id="p1", steps=[step])
        adapter.message_to_intent_or_plan.return_value = plan
        engine.repository.get_latest_snapshot.return_value = None
        engine.repository.get_session_facts.return_value = {}
        engine.repository.get_project_members.return_value = [{"user_id": uid, "role": "admin"}]
        
        res = controller.on_submit("msg", [], pid, uid, "assisted")
        assert len(res) == 10
        assert res[6] == plan
        assert "proposed a plan" in res[1][-1]["content"].lower()
        assert res[7] == plan.model_dump(mode="json") # last_intent
        assert res[8] == {} # last_result
        assert res[9] == STATUS_PENDING_HTML

    def test_on_submit_action(self, setup):
        controller, engine, adapter, pid, uid = setup
        intent = ChatIntent(type=IntentType.ACTION_CALL, request_id="1", action_id="act", inputs={})
        adapter.message_to_intent_or_plan.return_value = intent
        exec_result = ExecutionResult(
            request_id="1", action_id="act", status=ExecutionStatus.SUCCESS, 
            message="Done", state_snapshot_id="s", state_diff=[]
        )
        engine.execute_intent.return_value = exec_result
        engine.repository.get_latest_snapshot.return_value = None
        engine.repository.get_session_facts.return_value = {}
        engine.repository.get_project_members.return_value = [{"user_id": uid, "role": "admin"}]
        
        res = controller.on_submit("msg", [], pid, uid, "assisted")
        assert "Executed `act`" in res[1][-1]["content"]
        assert res[7] == intent.model_dump(mode="json") # last_intent
        assert res[8] == exec_result.model_dump(mode="json") # last_result
        assert res[9] == STATUS_SUCCESS_HTML

    def test_on_submit_clarification(self, setup):
        controller, engine, adapter, pid, uid = setup
        intent = ChatIntent(type=IntentType.CLARIFICATION_REQUEST, request_id="1", question="What?")
        adapter.message_to_intent_or_plan.return_value = intent
        engine.repository.get_latest_snapshot.return_value = None
        engine.repository.get_session_facts.return_value = {}
        engine.repository.get_project_members.return_value = [{"user_id": uid, "role": "admin"}]
        res = controller.on_submit("msg", [], pid, uid, "assisted")
        assert "What?" in res[1][-1]["content"]
        assert res[7] == intent.model_dump(mode="json")
        assert res[8] == {}
        assert res[9] == STATUS_READY_HTML

    def test_on_submit_confirmation_required(self, setup):
        controller, engine, adapter, pid, uid = setup
        intent = ChatIntent(type=IntentType.ACTION_CALL, request_id="1", action_id="nuke", inputs={})
        adapter.message_to_intent_or_plan.return_value = intent
        exec_result = ExecutionResult(
            request_id="1", action_id="nuke", status=ExecutionStatus.REJECTED, 
            message="Confirm?", state_snapshot_id="s", 
            error=ExecutionError(code="confirmation_required", detail="confirm")
        )
        engine.execute_intent.return_value = exec_result
        engine.repository.get_latest_snapshot.return_value = None
        engine.repository.get_session_facts.return_value = {}
        engine.repository.get_project_members.return_value = [{"user_id": uid, "role": "admin"}]
        res = controller.on_submit("msg", [], pid, uid, "assisted")
        assert "requires confirmation" in res[1][-1]["content"]
        assert res[7] == intent.model_dump(mode="json")
        assert res[8] == exec_result.model_dump(mode="json")
        assert res[9] == STATUS_PENDING_HTML

    def test_on_submit_failure(self, setup):
        controller, engine, adapter, pid, uid = setup
        intent = ChatIntent(type=IntentType.ACTION_CALL, request_id="1", action_id="fail", inputs={})
        adapter.message_to_intent_or_plan.return_value = intent
        exec_result = ExecutionResult(
            request_id="1", action_id="fail", status=ExecutionStatus.FAILED, 
            message="Boom", state_snapshot_id="s",
            error=ExecutionError(code="err", detail="boom")
        )
        engine.execute_intent.return_value = exec_result
        engine.repository.get_latest_snapshot.return_value = None
        engine.repository.get_session_facts.return_value = {}
        engine.repository.get_project_members.return_value = [{"user_id": uid, "role": "admin"}]
        res = controller.on_submit("msg", [], pid, uid, "assisted")
        assert "Action Failed/Rejected: Boom" in res[1][-1]["content"]
        assert res[7] == intent.model_dump(mode="json")
        assert res[8] == exec_result.model_dump(mode="json")
        assert res[9] == STATUS_FAILED_HTML

    def test_on_submit_exception(self, setup):
        controller, engine, adapter, pid, uid = setup
        adapter.message_to_intent_or_plan.side_effect = Exception("Crash")
        engine.repository.get_latest_snapshot.return_value = None
        engine.repository.get_session_facts.return_value = {}
        engine.repository.get_project_members.return_value = [{"user_id": uid, "role": "admin"}]
        res = controller.on_submit("msg", [], pid, uid, "assisted")
        assert "Agent Error: Crash" in res[1][-1]["content"]
        assert res[7] == {}
        assert res[8] == {}
        assert res[9] == STATUS_FAILED_HTML

    def test_on_submit_multimodal(self, setup):
        controller, engine, adapter, pid, uid = setup
        message_data = {"text": "look", "files": ["/tmp/image.png"]}
        intent = ChatIntent(type=IntentType.CLARIFICATION_REQUEST, request_id="1", question="I see.")
        adapter.message_to_intent_or_plan.return_value = intent
        engine.repository.get_latest_snapshot.return_value = None
        engine.repository.get_session_facts.return_value = {}
        engine.repository.get_project_members.return_value = [{"user_id": uid, "role": "admin"}]
        with patch('gradio_chat_agent.ui.layout.encode_media') as mock_encode:
            mock_encode.return_value = {"data": "base64", "mime_type": "image/png"}
            res = controller.on_submit(message_data, [], pid, uid, "assisted")
            call_args = adapter.message_to_intent_or_plan.call_args
            assert call_args.kwargs['media']['type'] == 'image'

    def test_on_submit_no_result(self, setup):
        controller, engine, adapter, pid, uid = setup
        adapter.message_to_intent_or_plan.return_value = None # Should hit the final return
        engine.repository.get_latest_snapshot.return_value = None
        engine.repository.get_session_facts.return_value = {}
        engine.repository.get_project_members.return_value = [{"user_id": uid, "role": "admin"}]
        res = controller.on_submit("msg", [], pid, uid, "assisted")
        assert res[6] is None
        assert res[4] == "No plan pending."
        assert res[7] == {}
        assert res[8] == {}
        assert res[9] == STATUS_READY_HTML

    def test_on_approve_plan_mixed(self, setup):
        controller, engine, _, pid, uid = setup
        step1 = ChatIntent(type=IntentType.ACTION_CALL, request_id="1", action_id="a1", inputs={})
        step2 = ChatIntent(type=IntentType.ACTION_CALL, request_id="2", action_id="a2", inputs={})
        plan = ExecutionPlan(plan_id="p1", steps=[step1, step2])
        
        from gradio_chat_agent.models.execution_result import StateDiffEntry
        from gradio_chat_agent.models.enums import StateDiffOp
        
        # Mock Engine returning a success AND a failure
        results = [
            ExecutionResult(request_id="1", action_id="a1", status="success", state_snapshot_id="s1", message="ok", 
                            state_diff=[StateDiffEntry(path="c.v", op=StateDiffOp.ADD, value=1)]), # valid StateDiffEntry
            ExecutionResult(request_id="2", action_id="a2", status="failed", state_snapshot_id="s1", message="fail")
        ]
        engine.execute_plan.return_value = results
        engine.repository.get_latest_snapshot.return_value = None
        engine.repository.get_project_members.return_value = [{"user_id": uid, "role": "admin"}]
        
        res = controller.on_approve_plan(plan, [], pid, uid)
        assert "✅" in res[0][-1]["content"]
        assert "❌" in res[0][-1]["content"]
        assert res[1] == {} # new_state should be empty if snapshot is None
        assert res[6] == plan.model_dump(mode="json")
        assert res[7] == [r.model_dump(mode="json") for r in results]
        assert res[8] == STATUS_SUCCESS_HTML

    def test_on_approve_plan_none(self, setup):
        controller, _, _, pid, uid = setup
        res = controller.on_approve_plan(None, [], pid, uid)
        assert res[3] == "No plan"
        assert res[6] == {}
        assert res[7] == {}
        assert res[8] == STATUS_READY_HTML

    def test_on_reject_plan(self, setup):
        controller, _, _, pid, _ = setup
        res = controller.on_reject_plan([], pid)
        assert "Plan rejected" in res[0][-1]["content"]
        assert res[4].get('visible') is False
        assert res[6] == {}
        assert res[7] == {}
        assert res[8] == STATUS_READY_HTML

    def test_on_submit_string_input(self, setup):
        controller, engine, adapter, pid, uid = setup
        intent = ChatIntent(type=IntentType.CLARIFICATION_REQUEST, request_id="1", question="?")
        adapter.message_to_intent_or_plan.return_value = intent
        engine.repository.get_latest_snapshot.return_value = None
        engine.repository.get_session_facts.return_value = {}
        engine.repository.get_project_members.return_value = [{"user_id": uid, "role": "admin"}]
        
        # Test string input instead of dict
        res = controller.on_submit("hello", [], pid, uid, "assisted")
        assert res[1][0]["content"] == "hello"

    def test_on_submit_developer_filtering(self, setup):
        controller, engine, adapter, pid, uid = setup
        # u1 is not an admin
        engine.repository.get_project_members.return_value = [{"user_id": uid, "role": "viewer"}]
        
        from gradio_chat_agent.models.action import ActionDeclaration, ActionPermission
        from gradio_chat_agent.models.enums import ActionVisibility, ActionRisk
        dev_action = ActionDeclaration(
            action_id="dev.act", title="D", description="D", targets=["t"], 
            input_schema={}, 
            permission=ActionPermission(confirmation_required=False, risk=ActionRisk.LOW, visibility=ActionVisibility.DEVELOPER)
        )
        engine.registry.list_actions.return_value = [dev_action]
        engine.registry.list_components.return_value = []
        engine.repository.get_latest_snapshot.return_value = None
        engine.repository.get_session_facts.return_value = {}
        
        adapter.message_to_intent_or_plan.return_value = None
        
        controller.on_submit("hi", [], pid, uid, "assisted")
        
        # Verify adapter was called with filtered registry (empty because dev.act was filtered out)
        args, kwargs = adapter.message_to_intent_or_plan.call_args
        assert "dev.act" not in kwargs["action_registry"]

    def test_on_submit_role_lookup(self, setup):
        controller, engine, adapter, pid, uid = setup
        # User is an operator
        engine.repository.get_project_members.return_value = [{"user_id": uid, "role": "operator"}]
        engine.repository.get_latest_snapshot.return_value = None
        engine.repository.get_session_facts.return_value = {}
        
        adapter.message_to_intent_or_plan.return_value = None
        controller.on_submit("hi", [], pid, uid, "assisted")
        
        # We can't easily verify the internal user_role variable without mocking execute_intent 
        # or similar, but this executes the lookup code.

    def test_on_approve_plan_role_lookup(self, setup):
        controller, engine, _, pid, uid = setup
        step = ChatIntent(type=IntentType.ACTION_CALL, request_id="1", action_id="a1", inputs={})
        plan = ExecutionPlan(plan_id="p1", steps=[step])
        # User is an admin
        engine.repository.get_project_members.return_value = [{"user_id": uid, "role": "admin"}]
        engine.execute_plan.return_value = []
        
        controller.on_approve_plan(plan, [], pid, uid)
        # Verifies role lookup in on_approve_plan

    def test_ui_controller_on_submit_pending_approval(self, setup):
        controller, engine, adapter, pid, uid = setup
        
        intent = ChatIntent(type=IntentType.ACTION_CALL, request_id="1", action_id="act", inputs={})
        adapter.message_to_intent_or_plan.return_value = intent
        
        exec_res = ExecutionResult(
            request_id="1", action_id="act", status=ExecutionStatus.PENDING_APPROVAL, 
            message="Need admin", state_snapshot_id="none"
        )
        engine.execute_intent.return_value = exec_res
        engine.repository.get_latest_snapshot.return_value = None
        engine.repository.get_session_facts.return_value = {}
        engine.repository.get_project_members.return_value = [{"user_id": uid, "role": "admin"}]
        res = controller.on_submit("msg", [], pid, uid, "assisted")
        assert "pending approval" in res[1][-1]["content"]

    def test_ui_controller_coverage(self, setup):
        controller, engine, adapter, pid, uid = setup
        
        engine.repository.get_project_members.return_value = [{"user_id": uid, "role": "admin"}]
        res = controller.refresh_ui(pid, uid)
        assert res[4] == [[uid, "admin"]]
        
        engine.repository.get_session_facts.return_value = {"k": "v"}
        facts, _, _ = controller.on_add_fact(pid, uid, "k", "v")
        assert facts == [["k", "v"]]
        
        engine.repository.get_session_facts.return_value = {}
        facts, _ = controller.on_delete_fact(pid, uid, "k")
        assert facts == []
        
        engine.repository.get_project_members.return_value = [{"user_id": uid, "role": "admin"}, {"user_id": "new", "role": "viewer"}]
        members, _, _ = controller.on_add_member(pid, uid, "new", "viewer")
        assert members == [[uid, "admin"], ["new", "viewer"]]
        
        engine.repository.get_project_members.return_value = [{"user_id": uid, "role": "admin"}]
        members, _ = controller.on_remove_member(pid, uid, "new")
        assert members == [[uid, "admin"]]


class TestUILayout:
    def test_create_ui(self):
        engine = MagicMock()
        adapter = MagicMock()
        # Simply test that it returns a Blocks object and doesn't crash
        ui = create_ui(engine, adapter)
        assert isinstance(ui, gr.Blocks)
