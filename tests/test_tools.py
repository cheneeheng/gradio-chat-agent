import pytest
from unittest.mock import patch, MagicMock
from gradio_chat_agent.persistence.sql_repository import SQLStateRepository


class TestTools:
    def test_load_policy_tool(self, tmp_path):
        import gradio_chat_agent.tools.load_policy as tool
        policy_file = tmp_path / "policy.yaml"
        policy_file.write_text("limits:\n  rate:\n    per_minute: 10")
        db_file = tmp_path / "test.db"
        db_url = f"sqlite:///{db_file}"
        tool.load_policy(str(policy_file), "p1", db_url)
        repo = SQLStateRepository(db_url)
        assert repo.get_project_limits("p1")["limits"]["rate"]["per_minute"] == 10

    def test_load_policy_main(self, tmp_path):
        policy_file = tmp_path / "policy.yaml"
        policy_file.write_text("limits: {}")
        # Patch the class method directly in its original module
        with patch("gradio_chat_agent.persistence.sql_repository.SQLStateRepository.set_project_limits") as mock_set:
            with patch("sys.argv", ["load_policy.py", str(policy_file), "--project-id", "p1"]):
                import runpy
                runpy.run_path("src/gradio_chat_agent/tools/load_policy.py", run_name="__main__")
                mock_set.assert_called()
