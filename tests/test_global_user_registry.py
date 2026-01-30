import pytest
from gradio_chat_agent.api.endpoints import ApiEndpoints
from gradio_chat_agent.execution.engine import ExecutionEngine
from gradio_chat_agent.persistence.in_memory import InMemoryStateRepository
from gradio_chat_agent.persistence.sql_repository import SQLStateRepository
from gradio_chat_agent.registry.in_memory import InMemoryRegistry

class TestGlobalUserRegistry:
    @pytest.fixture
    def setup(self):
        repo = InMemoryStateRepository()
        engine = ExecutionEngine(InMemoryRegistry(), repo)
        api = ApiEndpoints(engine)
        return api, repo

    def test_list_and_delete_users_api(self, setup):
        api, repo = setup
        repo.create_user("u1", "h", full_name="N1")
        repo.create_user("u2", "h", full_name="N2")
        
        # List
        res = api.list_users(user_id="admin")
        assert len(res["data"]) == 2
        
        # Delete
        api.delete_user("u1", user_id="admin")
        res2 = api.list_users(user_id="admin")
        assert len(res2["data"]) == 1
        assert res2["data"][0]["id"] == "u2"

    def test_delete_user_sql(self):
        repo = SQLStateRepository("sqlite:///:memory:")
        repo.create_user("u1", "h")
        repo.add_project_member("p1", "u1", "admin")
        
        # Verify exists
        assert len(repo.list_users()) == 1
        assert len(repo.get_project_members("p1")) == 1
        
        # Delete
        repo.delete_user("u1")
        assert len(repo.list_users()) == 0
        assert len(repo.get_project_members("p1")) == 0

    def test_list_users_sql_empty(self):
        repo = SQLStateRepository("sqlite:///:memory:")
        # Default admin might be there if bootstrap ran, but here we use clean repo
        # Actually SQLStateRepository ctor might NOT run bootstrap unless app.py does.
        # But list_users might return [] or more.
        res = repo.list_users()
        # Filter out default admin if exists
        users = [u for u in res if u['id'] != 'admin']
        assert len(users) == 0
