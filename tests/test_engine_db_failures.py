from unittest.mock import MagicMock
import pytest
from gradio_chat_agent.execution.engine import ExecutionEngine
from gradio_chat_agent.persistence.in_memory import InMemoryStateRepository
from gradio_chat_agent.registry.in_memory import InMemoryRegistry
from gradio_chat_agent.models.intent import ChatIntent
from gradio_chat_agent.models.enums import IntentType, ExecutionStatus

class TestEngineDBFailures:
    @pytest.fixture
    def setup(self):
        registry = InMemoryRegistry()
        repository = InMemoryStateRepository()
        engine = ExecutionEngine(registry, repository)
        project_id = "proj-fail"
        return engine, repository, project_id

    def test_create_rejection_db_fail(self, setup):
        engine, repo, pid = setup
        
        # Mock save_execution to fail
        repo.save_execution = MagicMock(side_effect=Exception("DB Error"))
        
        intent = ChatIntent(
            type=IntentType.ACTION_CALL,
            request_id="1",
            action_id="missing"
        )
        
        # This calls _create_rejection internally
        result = engine.execute_intent(pid, intent)
        
        assert result.status == ExecutionStatus.REJECTED
        # Verify the exception was suppressed and we got a result
        assert repo.save_execution.called

    def test_create_failure_db_fail(self, setup):
        engine, repo, pid = setup
        
        # Mock save_execution to fail
        repo.save_execution = MagicMock(side_effect=Exception("DB Error"))
        
        # Create an intent that triggers a failure (e.g. no handler)
        # Note: We need a valid action in registry but no handler to trigger _create_failure
        # Or we can just call _create_failure directly which is easier/safer for coverage
        
        intent = ChatIntent(
            type=IntentType.ACTION_CALL,
            request_id="1",
            action_id="some.action"
        )
        
        result = engine._create_failure(pid, intent, "Some failure")
        
        assert result.status == ExecutionStatus.FAILED
        assert repo.save_execution.called
