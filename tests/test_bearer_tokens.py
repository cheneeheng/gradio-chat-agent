import pytest
from datetime import UTC, datetime, timedelta
from gradio_chat_agent.api.endpoints import ApiEndpoints
from gradio_chat_agent.execution.engine import ExecutionEngine
from gradio_chat_agent.persistence.in_memory import InMemoryStateRepository
from gradio_chat_agent.persistence.sql_repository import SQLStateRepository
from gradio_chat_agent.registry.in_memory import InMemoryRegistry


class TestBearerTokens:
    @pytest.fixture
    def setup_in_memory(self):
        repo = InMemoryStateRepository()
        engine = ExecutionEngine(InMemoryRegistry(), repo)
        api = ApiEndpoints(engine)
        return api, repo

    def test_token_lifecycle_in_memory(self, setup_in_memory):
        api, repo = setup_in_memory
        repo.create_user("u1", "h")

        # Create
        res = api.create_api_token("u1", "T1", user_id="admin")
        token = res["data"]["token"]
        assert token.startswith("sk-")

        # List
        res_list = api.list_api_tokens("u1", user_id="admin")
        assert len(res_list["data"]) == 1
        assert res_list["data"][0]["name"] == "T1"

        # Validate
        assert repo.validate_api_token(token) == "u1"

        # Revoke
        api.revoke_api_token(token, user_id="admin")
        assert repo.validate_api_token(token) is None

    def test_token_validation_expiry(self, setup_in_memory):
        api, repo = setup_in_memory
        # Expired
        repo.create_api_token(
            "u1",
            "E",
            "expired-token",
            expires_at=datetime.now() - timedelta(seconds=1),
        )
        assert repo.validate_api_token("expired-token") is None

        # Future
        repo.create_api_token(
            "u1",
            "F",
            "valid-token",
            expires_at=datetime.now() + timedelta(hours=1),
        )
        assert repo.validate_api_token("valid-token") == "u1"

    def test_token_lifecycle_sql(self):
        repo = SQLStateRepository("sqlite:///:memory:")
        engine = ExecutionEngine(InMemoryRegistry(), repo)
        api = ApiEndpoints(engine)

        repo.create_user("u1", "h")
        res = api.create_api_token("u1", "T", user_id="admin")
        token = res["data"]["token"]

        assert repo.validate_api_token(token) == "u1"

        # Expiry in SQL
        repo.create_api_token(
            "u1",
            "E",
            "tok-exp",
            expires_at=datetime.now(UTC) - timedelta(seconds=1),
        )
        assert repo.validate_api_token("tok-exp") is None

    def test_api_permission_denied(self, setup_in_memory):
        api, _ = setup_in_memory
        # Create token requires system admin
        res = api.create_api_token("u1", "T", user_id="alice")
        assert res["code"] == 1
        assert "Permission denied" in res["message"]

        # List token for self is allowed? No, currently only system admin in logic
        res2 = api.list_api_tokens("u1", user_id="u1")
        assert (
            res2["code"] == 0
        )  # Wait, I added `user_id != owner_user_id` check

        res3 = api.list_api_tokens("u1", user_id="bob")
        assert res3["code"] == 1

    def test_revoke_permission_denied(self, setup_in_memory):
        api, _ = setup_in_memory
        res = api.revoke_api_token("any", user_id="bob")
        assert res["code"] == 1

    def test_validate_api_token_missing(self, setup_in_memory):
        _, repo = setup_in_memory
        assert repo.validate_api_token("missing") is None
