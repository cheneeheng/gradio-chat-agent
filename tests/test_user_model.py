import pytest
from gradio_chat_agent.persistence.in_memory import InMemoryStateRepository
from gradio_chat_agent.persistence.sql_repository import SQLStateRepository

class TestUserModelPersistence:
    @pytest.mark.parametrize("repo_class, connection", [
        (InMemoryStateRepository, None),
        (SQLStateRepository, "sqlite:///:memory:")
    ])
    def test_user_lifecycle(self, repo_class, connection):
        if connection:
            repo = repo_class(connection)
        else:
            repo = repo_class()
            
        uid = "bob"
        pwd = "hash1"
        
        # Initial: missing
        assert repo.get_user(uid) is None
        
        # Create
        repo.create_user(uid, pwd)
        user = repo.get_user(uid)
        assert user is not None
        assert user["id"] == uid
        assert user["password_hash"] == pwd
        
        # Update
        new_pwd = "hash2"
        repo.update_user_password(uid, new_pwd)
        user_updated = repo.get_user(uid)
        assert user_updated["password_hash"] == new_pwd
        
    def test_update_missing_user_sql(self):
        repo = SQLStateRepository("sqlite:///:memory:")
        # Should not raise exception
        repo.update_user_password("missing", "hash")
        assert repo.get_user("missing") is None
