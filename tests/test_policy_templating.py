import pytest
from gradio_chat_agent.api.endpoints import ApiEndpoints
from gradio_chat_agent.execution.engine import ExecutionEngine
from gradio_chat_agent.persistence.in_memory import InMemoryStateRepository
from gradio_chat_agent.registry.in_memory import InMemoryRegistry
from gradio_chat_agent.models.enums import ProjectOp

class TestPolicyTemplating:
    def test_default_policy_on_create(self):
        repo = InMemoryStateRepository()
        api = ApiEndpoints(ExecutionEngine(InMemoryRegistry(), repo))
        
        res = api.manage_project(ProjectOp.CREATE, name="New", user_id="admin")
        pid = res["data"]["project_id"]
        
        policy = repo.get_project_limits(pid)
        assert policy["limits"]["rate"]["per_minute"] == 10
        assert policy["limits"]["budget"]["daily"] == 500.0
