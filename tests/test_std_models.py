import pytest
from gradio_chat_agent.execution.engine import ExecutionEngine
from gradio_chat_agent.models.enums import IntentType, ExecutionStatus
from gradio_chat_agent.models.intent import ChatIntent
from gradio_chat_agent.models.state_snapshot import StateSnapshot
from gradio_chat_agent.persistence.in_memory import InMemoryStateRepository
from gradio_chat_agent.registry.in_memory import InMemoryRegistry
from gradio_chat_agent.registry.std_models import (
    model_selector_component,
    prompt_editor_component,
    output_panel_component,
    select_model_action,
    select_model_handler,
    load_model_action,
    load_model_handler,
    run_inference_action,
    run_inference_handler,
    MODEL_SELECTOR_ID,
    PROMPT_EDITOR_ID,
    OUTPUT_PANEL_ID,
)

class TestStdModels:
    @pytest.fixture
    def setup(self):
        registry = InMemoryRegistry()
        repository = InMemoryStateRepository()
        engine = ExecutionEngine(registry, repository)
        project_id = "test-std-models"

        registry.register_component(model_selector_component)
        registry.register_component(prompt_editor_component)
        registry.register_component(output_panel_component)

        registry.register_action(select_model_action, select_model_handler)
        registry.register_action(load_model_action, load_model_handler)
        registry.register_action(run_inference_action, run_inference_handler)

        # Initial state
        initial_state = {
            MODEL_SELECTOR_ID: {
                "selected_model": None,
                "loaded": False,
                "available_models": ["gpt-4o", "gpt-4o-mini"]
            },
            PROMPT_EDITOR_ID: {"text": "Original prompt"},
            OUTPUT_PANEL_ID: {
                "latest_response": None,
                "streaming": False,
                "tokens_used": 0
            }
        }
        repository.save_snapshot(project_id, StateSnapshot(snapshot_id="init", components=initial_state))

        return engine, repository, project_id

    def test_select_model_success(self, setup):
        engine, repo, pid = setup
        intent = ChatIntent(
            type=IntentType.ACTION_CALL,
            request_id="r1",
            action_id="model.select",
            inputs={"model_name": "gpt-4o"}
        )
        res = engine.execute_intent(pid, intent, user_roles=["admin"])
        assert res.status == ExecutionStatus.SUCCESS
        
        latest = repo.get_latest_snapshot(pid)
        assert latest.components[MODEL_SELECTOR_ID]["selected_model"] == "gpt-4o"
        assert latest.components[MODEL_SELECTOR_ID]["loaded"] is False

    def test_select_model_invalid(self, setup):
        engine, repo, pid = setup
        intent = ChatIntent(
            type=IntentType.ACTION_CALL,
            request_id="r1",
            action_id="model.select",
            inputs={"model_name": "ghost-model"}
        )
        res = engine.execute_intent(pid, intent, user_roles=["admin"])
        assert res.status == ExecutionStatus.REJECTED
        assert "Precondition failed" in res.message

    def test_load_model_success(self, setup):
        engine, repo, pid = setup
        # First select
        engine.execute_intent(pid, ChatIntent(type=IntentType.ACTION_CALL, request_id="r1", action_id="model.select", inputs={"model_name": "gpt-4o"}), user_roles=["admin"])
        
        # Then load
        intent = ChatIntent(type=IntentType.ACTION_CALL, request_id="r2", action_id="model.load", inputs={})
        res = engine.execute_intent(pid, intent, user_roles=["admin"])
        assert res.status == ExecutionStatus.SUCCESS
        
        latest = repo.get_latest_snapshot(pid)
        assert latest.components[MODEL_SELECTOR_ID]["loaded"] is True

    def test_load_model_fail_not_selected(self, setup):
        engine, repo, pid = setup
        # Try load without select
        intent = ChatIntent(type=IntentType.ACTION_CALL, request_id="r1", action_id="model.load", inputs={})
        res = engine.execute_intent(pid, intent, user_roles=["admin"])
        assert res.status == ExecutionStatus.REJECTED
        assert "A model must be selected first" in res.message

    def test_run_inference_success(self, setup):
        engine, repo, pid = setup
        # Setup: select and load
        engine.execute_intent(pid, ChatIntent(type=IntentType.ACTION_CALL, request_id="r1", action_id="model.select", inputs={"model_name": "gpt-4o"}), user_roles=["admin"])
        engine.execute_intent(pid, ChatIntent(type=IntentType.ACTION_CALL, request_id="r2", action_id="model.load", inputs={}), user_roles=["admin"])
        
        # Run inference
        intent = ChatIntent(type=IntentType.ACTION_CALL, request_id="r3", action_id="inference.run", inputs={"prompt_override": "Hello"})
        res = engine.execute_intent(pid, intent, user_roles=["admin"])
        assert res.status == ExecutionStatus.SUCCESS
        
        latest = repo.get_latest_snapshot(pid)
        assert "Simulated response" in latest.components[OUTPUT_PANEL_ID]["latest_response"]
        assert latest.components[OUTPUT_PANEL_ID]["tokens_used"] > 0

    def test_run_inference_fail_not_loaded(self, setup):
        engine, repo, pid = setup
        # Try run without load
        intent = ChatIntent(type=IntentType.ACTION_CALL, request_id="r1", action_id="inference.run", inputs={})
        res = engine.execute_intent(pid, intent, user_roles=["admin"])
        assert res.status == ExecutionStatus.REJECTED
        assert "Model must be loaded" in res.message

    def test_run_inference_use_snapshot_prompt(self, setup):
        engine, repo, pid = setup
        # Setup: select and load
        engine.execute_intent(pid, ChatIntent(type=IntentType.ACTION_CALL, request_id="r1", action_id="model.select", inputs={"model_name": "gpt-4o"}), user_roles=["admin"])
        engine.execute_intent(pid, ChatIntent(type=IntentType.ACTION_CALL, request_id="r2", action_id="model.load", inputs={}), user_roles=["admin"])
        
        # Run inference WITHOUT override
        intent = ChatIntent(type=IntentType.ACTION_CALL, request_id="r3", action_id="inference.run", inputs={})
        res = engine.execute_intent(pid, intent, user_roles=["admin"])
        assert res.status == ExecutionStatus.SUCCESS
        
        latest = repo.get_latest_snapshot(pid)
        assert "Original prompt" in latest.components[OUTPUT_PANEL_ID]["latest_response"]

    def test_select_model_default_state(self):
        # Test handler with empty initial state for components
        snapshot = StateSnapshot(snapshot_id="s1", components={})
        res_comps, diff, msg = select_model_handler({"model_name": "gpt-4o"}, snapshot)
        assert res_comps[MODEL_SELECTOR_ID]["selected_model"] == "gpt-4o"
        assert len(diff) == 2

    def test_run_inference_default_state(self):
        snapshot = StateSnapshot(snapshot_id="s1", components={})
        res_comps, diff, msg = run_inference_handler({"prompt_override": "Hi"}, snapshot)
        assert "Hi" in res_comps[OUTPUT_PANEL_ID]["latest_response"]
