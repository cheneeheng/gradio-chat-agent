import pytest
from gradio_chat_agent.api.endpoints import ApiEndpoints
from gradio_chat_agent.execution.engine import ExecutionEngine
from gradio_chat_agent.persistence.in_memory import InMemoryStateRepository
from gradio_chat_agent.persistence.sql_repository import SQLStateRepository
from gradio_chat_agent.registry.in_memory import InMemoryRegistry
from gradio_chat_agent.models.enums import WebhookOp

class TestSecretRotation:
    @pytest.fixture
    def setup_in_memory(self):
        repo = InMemoryStateRepository()
        engine = ExecutionEngine(InMemoryRegistry(), repo)
        api = ApiEndpoints(engine)
        return api, repo

    def test_rotate_webhook_secret_in_memory(self, setup_in_memory):
        api, repo = setup_in_memory
        webhook_id = "wh1"
        repo.save_webhook({"id": webhook_id, "project_id": "p1", "action_id": "a", "secret": "old"})
        
        # Rotate to specific secret
        res = api.rotate_webhook_secret(webhook_id, new_secret="new")
        assert res["code"] == 0
        assert repo.get_webhook(webhook_id)["secret"] == "new"
        
        # Rotate to random
        res2 = api.rotate_webhook_secret(webhook_id)
        assert res2["data"]["new_secret"] != "new"
        assert repo.get_webhook(webhook_id)["secret"] == res2["data"]["new_secret"]

    def test_rotate_webhook_secret_sql(self):
        repo = SQLStateRepository("sqlite:///:memory:")
        engine = ExecutionEngine(InMemoryRegistry(), repo)
        api = ApiEndpoints(engine)
        
        webhook_id = "wh1"
        repo.save_webhook({"id": webhook_id, "project_id": "p1", "action_id": "a", "secret": "old"})
        
        api.rotate_webhook_secret(webhook_id, new_secret="new")
        
        # Retrieval should be decrypted
        assert repo.get_webhook(webhook_id)["secret"] == "new"
        
        # DB should be encrypted
        from gradio_chat_agent.persistence.models import Webhook
        with repo.SessionLocal() as session:
            row = session.get(Webhook, webhook_id)
            assert row.secret != "new"

    def test_rotate_missing_webhook(self, setup_in_memory):
        api, repo = setup_in_memory
        # Should not crash, just do nothing or handle gracefully
        api.rotate_webhook_secret("missing", "new")
        assert repo.get_webhook("missing") is None
