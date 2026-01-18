import pytest
from gradio_chat_agent.execution.engine import ExecutionEngine
from gradio_chat_agent.models.enums import IntentType, ExecutionStatus
from gradio_chat_agent.models.intent import ChatIntent
from gradio_chat_agent.models.state_snapshot import StateSnapshot
from gradio_chat_agent.persistence.in_memory import InMemoryStateRepository
from gradio_chat_agent.registry.in_memory import InMemoryRegistry
from gradio_chat_agent.registry.std_lib import (
    text_input_component,
    text_input_set_action,
    text_input_set_handler,
    slider_component,
    slider_set_action,
    slider_set_handler,
    status_indicator_component,
    status_indicator_update_action,
    status_indicator_update_handler,
    TEXT_INPUT_ID,
    SLIDER_ID,
    STATUS_INDICATOR_ID,
)

class TestStdLib:
    @pytest.fixture
    def setup(self):
        registry = InMemoryRegistry()
        repository = InMemoryStateRepository()
        engine = ExecutionEngine(registry, repository)
        project_id = "test-std-lib"

        registry.register_component(text_input_component)
        registry.register_component(slider_component)
        registry.register_component(status_indicator_component)

        registry.register_action(text_input_set_action, text_input_set_handler)
        registry.register_action(slider_set_action, slider_set_handler)
        registry.register_action(status_indicator_update_action, status_indicator_update_handler)

        return engine, repository, project_id

    def test_text_input_set(self, setup):
        engine, repo, pid = setup
        intent = ChatIntent(
            type=IntentType.ACTION_CALL,
            request_id="r1",
            action_id="std.text.input.set",
            inputs={"value": "new text"}
        )
        res = engine.execute_intent(pid, intent, user_roles=["admin"])
        assert res.status == ExecutionStatus.SUCCESS
        
        latest = repo.get_latest_snapshot(pid)
        assert latest.components[TEXT_INPUT_ID]["value"] == "new text"

    def test_slider_set(self, setup):
        engine, repo, pid = setup
        intent = ChatIntent(
            type=IntentType.ACTION_CALL,
            request_id="r1",
            action_id="std.slider.set",
            inputs={"value": 42.5}
        )
        res = engine.execute_intent(pid, intent, user_roles=["admin"])
        assert res.status == ExecutionStatus.SUCCESS
        
        latest = repo.get_latest_snapshot(pid)
        assert latest.components[SLIDER_ID]["value"] == 42.5

    def test_status_indicator_update(self, setup):
        engine, repo, pid = setup
        intent = ChatIntent(
            type=IntentType.ACTION_CALL,
            request_id="r1",
            action_id="std.status.indicator.update",
            inputs={"status": "online", "message": "All good"}
        )
        res = engine.execute_intent(pid, intent, user_roles=["admin"])
        assert res.status == ExecutionStatus.SUCCESS
        
        latest = repo.get_latest_snapshot(pid)
        assert latest.components[STATUS_INDICATOR_ID]["status"] == "online"
        assert latest.components[STATUS_INDICATOR_ID]["message"] == "All good"
        assert "last_updated" in latest.components[STATUS_INDICATOR_ID]

    def test_status_indicator_partial_update(self, setup):
        engine, repo, pid = setup
        # Initial state
        repo.save_snapshot(pid, StateSnapshot(snapshot_id="0", components={STATUS_INDICATOR_ID: {"status": "away", "message": "old"}}))
        
        # Update only status
        intent = ChatIntent(
            type=IntentType.ACTION_CALL,
            request_id="r1",
            action_id="std.status.indicator.update",
            inputs={"status": "online"}
        )
        engine.execute_intent(pid, intent, user_roles=["admin"])
        
        latest = repo.get_latest_snapshot(pid)
        assert latest.components[STATUS_INDICATOR_ID]["status"] == "online"
        assert latest.components[STATUS_INDICATOR_ID]["message"] == "old"

    def test_text_input_handler_default_state(self):
        snapshot = StateSnapshot(snapshot_id="s1", components={})
        res_comps, diff, msg = text_input_set_handler({"value": "hi"}, snapshot)
        assert res_comps[TEXT_INPUT_ID]["value"] == "hi"

    def test_slider_handler_default_state(self):
        snapshot = StateSnapshot(snapshot_id="s1", components={})
        res_comps, diff, msg = slider_set_handler({"value": 10}, snapshot)
        assert res_comps[SLIDER_ID]["value"] == 10

    def test_status_indicator_handler_default_state(self):
        snapshot = StateSnapshot(snapshot_id="s1", components={})
        res_comps, diff, msg = status_indicator_update_handler({"status": "busy"}, snapshot)
        assert res_comps[STATUS_INDICATOR_ID]["status"] == "busy"
        assert len(diff) == 1