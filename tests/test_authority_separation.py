import pytest
from gradio_chat_agent.api.endpoints import ApiEndpoints
from gradio_chat_agent.execution.engine import ExecutionEngine
from gradio_chat_agent.persistence.in_memory import InMemoryStateRepository
from gradio_chat_agent.registry.in_memory import InMemoryRegistry
from gradio_chat_agent.models.enums import ProjectOp

class TestAuthoritySeparation:
    @pytest.fixture
    def api(self):
        return ApiEndpoints(ExecutionEngine(InMemoryRegistry(), InMemoryStateRepository()))

    def test_manage_project_system_admin_only(self, api):
        # Denied
        res = api.manage_project(ProjectOp.CREATE, name="P", user_id="bob")
        assert res["code"] == 1
        assert "System Admin required" in res["message"]
        
        # Allowed
        res2 = api.manage_project(ProjectOp.CREATE, name="P", user_id="admin")
        assert res2["code"] == 0
        assert "Project created" in res2["message"]

    def test_list_users_system_admin_only(self, api):
        res = api.list_users(user_id="alice")
        assert res["code"] == 1
        
        res2 = api.list_users(user_id="admin")
        assert res2["code"] == 0

    def test_delete_user_system_admin_only(self, api):
        res = api.delete_user("some_user", user_id="alice")
        assert res["code"] == 1
        
        res2 = api.delete_user("some_user", user_id="admin")
        assert res2["code"] == 0
