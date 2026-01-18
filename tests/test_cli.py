import pytest
from unittest.mock import patch, MagicMock
from typer.testing import CliRunner
from gradio_chat_agent.cli import app, get_repo
from gradio_chat_agent.persistence.sql_repository import SQLStateRepository
import os

runner = CliRunner()

class TestCLI:
    @pytest.fixture(autouse=True)
    def setup_db(self, tmp_path):
        db_file = tmp_path / "test_cli.db"
        self.db_url = f"sqlite:///{db_file}"
        os.environ["DATABASE_URL"] = self.db_url
        yield
        if "DATABASE_URL" in os.environ:
            del os.environ["DATABASE_URL"]

    def test_project_create_and_list(self):
        result = runner.invoke(app, ["project", "create", "--name", "Test Project", "--project-id", "test-p"])
        assert result.exit_code == 0
        assert "Project created: Test Project (ID: test-p)" in result.output
        
        result = runner.invoke(app, ["project", "list"])
        assert result.exit_code == 0
        assert "test-p: Test Project" in result.output

    def test_user_create_and_reset(self):
        # user create prompts for password
        result = runner.invoke(app, ["user", "create", "--username", "alice"], input="password123\n")
        assert result.exit_code == 0
        assert "User created: alice" in result.output
        
        repo = get_repo()
        with repo.SessionLocal() as session:
            from gradio_chat_agent.persistence.models import User
            user = session.get(User, "alice")
            assert user is not None
            
        result = runner.invoke(app, ["user", "password-reset", "--username", "alice"], input="newpassword\n")
        assert result.exit_code == 0
        assert "Password updated for user: alice" in result.output

    def test_webhook_list(self):
        repo = get_repo()
        repo.save_webhook({"id": "wh-123", "project_id": "p1", "action_id": "act", "secret": "s", "enabled": True})
        
        result = runner.invoke(app, ["webhook", "list"])
        assert result.exit_code == 0
        assert "wh-123 (Project: p1, Action: act)" in result.output
        
        result = runner.invoke(app, ["webhook", "list", "--project-id", "p2"])
        assert result.exit_code == 0
        assert "No webhooks found" in result.output

    def test_project_validate(self, tmp_path):
        # Valid policy
        valid_policy = tmp_path / "valid.yaml"
        valid_policy.write_text("project_id: 1\nlimits:\n  rate:\n    per_minute: 10")
        result = runner.invoke(app, ["project", "validate", str(valid_policy)])
        assert result.exit_code == 0
        assert "is valid" in result.output

        # Invalid policy (bad enum)
        invalid_policy = tmp_path / "invalid.yaml"
        invalid_policy.write_text("approvals:\n  - min_cost: 10\n    required_role: unknown")
        result = runner.invoke(app, ["project", "validate", str(invalid_policy)])
        assert result.exit_code == 1
        assert "Validation Error" in result.output
        assert "unknown" in result.output

    def test_project_list_empty(self):
        with patch("gradio_chat_agent.cli.get_repo") as mock_get:
            mock_repo = MagicMock()
            mock_repo.list_projects.return_value = []
            mock_get.return_value = mock_repo
            
            result = runner.invoke(app, ["project", "list"])
            assert result.exit_code == 0
            assert "No projects found" in result.output

    def test_project_validate_errors(self, tmp_path):
        # File not found
        result = runner.invoke(app, ["project", "validate", "nonexistent.yaml"])
        assert result.exit_code == 1
        assert "File not found" in result.output
        
        # Invalid YAML
        bad_yaml = tmp_path / "bad.yaml"
        bad_yaml.write_text("key: : value")
        result = runner.invoke(app, ["project", "validate", str(bad_yaml)])
        assert result.exit_code == 1
        assert "Error parsing YAML" in result.output
        
        # Missing schema (Mocking Path.exists)
        valid_policy = tmp_path / "valid.yaml"
        valid_policy.write_text("limits: {}")
        
        from pathlib import Path
        original_exists = Path.exists
        
        def side_effect(self):
            if "policy.schema.json" in str(self):
                return False
            return original_exists(self)
            
        with patch.object(Path, "exists", side_effect=side_effect, autospec=True):
            result = runner.invoke(app, ["project", "validate", str(valid_policy)])
            assert result.exit_code == 0
            assert "Skipping schema check" in result.output

        # Generic Exception during validation
        with patch("gradio_chat_agent.cli.json_validate", side_effect=Exception("Generic Error")):
             result = runner.invoke(app, ["project", "validate", str(valid_policy)])
             assert result.exit_code == 1
             assert "Error: Generic Error" in result.output

    def test_cli_main_block(self):
        import runpy
        from typer import Typer
        with patch.object(Typer, "__call__") as mock_call:
            runpy.run_path("src/gradio_chat_agent/cli.py", run_name="__main__")
            mock_call.assert_called_once()
