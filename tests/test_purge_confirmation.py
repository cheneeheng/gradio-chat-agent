import pytest
from gradio_chat_agent.api.endpoints import ApiEndpoints
from gradio_chat_agent.execution.engine import ExecutionEngine
from gradio_chat_agent.persistence.in_memory import InMemoryStateRepository
from gradio_chat_agent.registry.in_memory import InMemoryRegistry
from gradio_chat_agent.models.enums import ProjectOp

class TestPurgeConfirmation:
    def test_purge_gate(self):
        repo = InMemoryStateRepository()
        api = ApiEndpoints(ExecutionEngine(InMemoryRegistry(), repo))
        repo.create_project("p1", "P1")
        
        # 1. Denied (no confirm)
        res = api.manage_project(ProjectOp.PURGE, project_id="p1", user_id="admin", confirmed=False)
        assert res["code"] == 1
        assert "Confirmation required" in res["message"]
        assert len(repo.list_projects()) == 1
        
        # 2. Allowed (confirmed)
        res2 = api.manage_project(ProjectOp.PURGE, project_id="p1", user_id="admin", confirmed=True)
        assert res2["code"] == 0
        assert "Project purged" in res2["message"]
        assert len(repo.list_projects()) == 0
