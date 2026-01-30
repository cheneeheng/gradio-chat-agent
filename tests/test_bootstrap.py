import os
import pytest
from unittest.mock import patch, MagicMock
from gradio_chat_agent.app import bootstrap_admin
from gradio_chat_agent.persistence.sql_repository import SQLStateRepository

class TestBootstrap:
    def test_bootstrap_enabled_default(self):
        repo = SQLStateRepository("sqlite:///:memory:")
        with patch.dict("os.environ", {}, clear=True):
            # Should be enabled by default
            bootstrap_admin(repo)
            assert repo.get_user("admin") is not None
            
    def test_bootstrap_disabled(self):
        repo = SQLStateRepository("sqlite:///:memory:")
        with patch.dict("os.environ", {"ALLOW_DEFAULT_ADMIN": "False"}):
            bootstrap_admin(repo)
            assert repo.get_user("admin") is None
            
    def test_bootstrap_skips_if_exists(self):
        repo = SQLStateRepository("sqlite:///:memory:")
        repo.create_user("admin", "custom_hash")
        
        with patch.object(repo, "create_user") as mock_create:
            bootstrap_admin(repo)
            mock_create.assert_not_called()
            
    def test_bootstrap_adds_to_default_project(self):
        repo = SQLStateRepository("sqlite:///:memory:")
        bootstrap_admin(repo)
        
        members = repo.get_project_members("default_project")
        assert any(m["user_id"] == "admin" and m["role"] == "admin" for m in members)
