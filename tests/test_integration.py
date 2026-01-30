import pytest
from unittest.mock import MagicMock, patch

from gradio_chat_agent.registry.in_memory import InMemoryRegistry
from gradio_chat_agent.persistence.in_memory import InMemoryStateRepository
from gradio_chat_agent.execution.engine import ExecutionEngine
from gradio_chat_agent.models.intent import ChatIntent
from gradio_chat_agent.models.enums import IntentType, ExecutionMode
from gradio_chat_agent.registry.demo_actions import (
    counter_component, set_action, set_handler
)

class TestIntegration:
    def test_full_execution_flow(self):
        # Setup
        registry = InMemoryRegistry()
        registry.register_component(counter_component)
        registry.register_action(set_action, set_handler)
        
        repo = InMemoryStateRepository()
        engine = ExecutionEngine(registry, repo)
        
        project_id = "test_proj"
        
        # Mock Adapter response (skip calling OpenAI)
        mock_intent = ChatIntent(
            type=IntentType.ACTION_CALL,
            request_id="req1",
            action_id="demo.counter.set",
            inputs={"value": 42},
            execution_mode=ExecutionMode.ASSISTED
        )
        
        # Simulate UI calling adapter
        # In integration test, we trust adapter works if unit tested, here we test Engine flow triggered by it.
        
        # Execute Intent
        result = engine.execute_intent(project_id, mock_intent, user_roles=["admin"])
        
        assert result.status == "success"
        assert "Counter set to 42" in result.message
        
        # Verify State
        snapshot = repo.get_latest_snapshot(project_id)
        assert snapshot is not None
        assert snapshot.components["demo.counter"]["value"] == 42
