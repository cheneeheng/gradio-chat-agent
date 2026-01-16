from unittest.mock import MagicMock, patch
import pytest
import gradio as gr
from gradio_chat_agent.ui.layout import UIController, create_ui
from gradio_chat_agent.execution.engine import ExecutionEngine
from gradio_chat_agent.chat.adapter import AgentAdapter
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
        assert len(res) == 5
        assert res[0] == {}

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

    def test_on_submit_plan(self, setup):
        controller, engine, adapter, pid, uid = setup
        step = ChatIntent(type=IntentType.ACTION_CALL, request_id="1", action_id="a1", inputs={})
        plan = ExecutionPlan(plan_id="p1", steps=[step])
        adapter.message_to_intent_or_plan.return_value = plan
        engine.repository.get_latest_snapshot.return_value = None
        engine.repository.get_session_facts.return_value = {}
        
        res = controller.on_submit("msg", [], pid, uid, "assisted")
        assert len(res) == 7
        assert res[6] == plan
        assert "proposed a plan" in res[1][-1]["content"].lower()

    def test_on_submit_action(self, setup):
        controller, engine, adapter, pid, uid = setup
        intent = ChatIntent(type=IntentType.ACTION_CALL, request_id="1", action_id="act", inputs={})
        adapter.message_to_intent_or_plan.return_value = intent
        engine.execute_intent.return_value = ExecutionResult(
            request_id="1", action_id="act", status=ExecutionStatus.SUCCESS, 
            message="Done", state_snapshot_id="s", state_diff=[]
        )
        engine.repository.get_latest_snapshot.return_value = None
        engine.repository.get_session_facts.return_value = {}
        
        res = controller.on_submit("msg", [], pid, uid, "assisted")
        assert "Executed `act`" in res[1][-1]["content"]

    def test_on_submit_clarification(self, setup):
        controller, engine, adapter, pid, uid = setup
        intent = ChatIntent(type=IntentType.CLARIFICATION_REQUEST, request_id="1", question="What?")
        adapter.message_to_intent_or_plan.return_value = intent
        engine.repository.get_latest_snapshot.return_value = None
        engine.repository.get_session_facts.return_value = {}
        res = controller.on_submit("msg", [], pid, uid, "assisted")
        assert "What?" in res[1][-1]["content"]

    def test_on_submit_confirmation_required(self, setup):
        controller, engine, adapter, pid, uid = setup
        intent = ChatIntent(type=IntentType.ACTION_CALL, request_id="1", action_id="nuke", inputs={})
        adapter.message_to_intent_or_plan.return_value = intent
        engine.execute_intent.return_value = ExecutionResult(
            request_id="1", action_id="nuke", status=ExecutionStatus.REJECTED, 
            message="Confirm?", state_snapshot_id="s", 
            error=ExecutionError(code="confirmation_required", detail="confirm")
        )
        engine.repository.get_latest_snapshot.return_value = None
        engine.repository.get_session_facts.return_value = {}
        res = controller.on_submit("msg", [], pid, uid, "assisted")
        assert "requires confirmation" in res[1][-1]["content"]

    def test_on_submit_failure(self, setup):
        controller, engine, adapter, pid, uid = setup
        intent = ChatIntent(type=IntentType.ACTION_CALL, request_id="1", action_id="fail", inputs={})
        adapter.message_to_intent_or_plan.return_value = intent
        engine.execute_intent.return_value = ExecutionResult(
            request_id="1", action_id="fail", status=ExecutionStatus.FAILED, 
            message="Boom", state_snapshot_id="s",
            error=ExecutionError(code="err", detail="boom")
        )
        engine.repository.get_latest_snapshot.return_value = None
        engine.repository.get_session_facts.return_value = {}
        res = controller.on_submit("msg", [], pid, uid, "assisted")
        assert "Action Failed/Rejected: Boom" in res[1][-1]["content"]

    def test_on_submit_exception(self, setup):
        controller, engine, adapter, pid, uid = setup
        adapter.message_to_intent_or_plan.side_effect = Exception("Crash")
        engine.repository.get_latest_snapshot.return_value = None
        engine.repository.get_session_facts.return_value = {}
        res = controller.on_submit("msg", [], pid, uid, "assisted")
        assert "Agent Error: Crash" in res[1][-1]["content"]

    def test_on_submit_multimodal(self, setup):
        controller, engine, adapter, pid, uid = setup
        message_data = {"text": "look", "files": ["/tmp/image.png"]}
        intent = ChatIntent(type=IntentType.CLARIFICATION_REQUEST, request_id="1", question="I see.")
        adapter.message_to_intent_or_plan.return_value = intent
        engine.repository.get_latest_snapshot.return_value = None
        engine.repository.get_session_facts.return_value = {}
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
        res = controller.on_submit("msg", [], pid, uid, "assisted")
        assert res[6] is None
        assert res[4] == "No plan pending."

    def test_on_approve_plan_mixed(self, setup):
        controller, engine, _, pid, uid = setup
        step1 = ChatIntent(type=IntentType.ACTION_CALL, request_id="1", action_id="a1", inputs={})
        step2 = ChatIntent(type=IntentType.ACTION_CALL, request_id="2", action_id="a2", inputs={})
        plan = ExecutionPlan(plan_id="p1", steps=[step1, step2])
        
        from gradio_chat_agent.models.execution_result import StateDiffEntry
        from gradio_chat_agent.models.enums import StateDiffOp
        
        # Mock Engine returning a success AND a failure
        engine.execute_plan.return_value = [
            ExecutionResult(request_id="1", action_id="a1", status="success", state_snapshot_id="s1", message="ok", 
                            state_diff=[StateDiffEntry(path="c.v", op=StateDiffOp.ADD, value=1)]), # valid StateDiffEntry
            ExecutionResult(request_id="2", action_id="a2", status="failed", state_snapshot_id="s1", message="fail")
        ]
        # Mock missing latest snapshot to cover line 312
        engine.repository.get_latest_snapshot.return_value = None
        
        res = controller.on_approve_plan(plan, [], pid, uid)
        assert "✅" in res[0][-1]["content"]
        assert "❌" in res[0][-1]["content"]
        assert res[1] == {} # new_state should be empty if snapshot is None

    def test_on_approve_plan_none(self, setup):
        controller, _, _, pid, uid = setup
        res = controller.on_approve_plan(None, [], pid, uid)
        assert res[3] == "No plan"

    def test_on_reject_plan(self, setup):
        controller, _, _, _, _ = setup
        res = controller.on_reject_plan([])
        assert "Plan rejected" in res[0][-1]["content"]
        assert res[2].get('visible') is False

def test_create_ui():
    engine = MagicMock()
    adapter = MagicMock()
    # Simply test that it returns a Blocks object and doesn't crash
    ui = create_ui(engine, adapter)
    assert isinstance(ui, gr.Blocks)