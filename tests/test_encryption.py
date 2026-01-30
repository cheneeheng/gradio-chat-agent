import pytest
import os
import base64
from gradio_chat_agent.utils import SecretManager
from gradio_chat_agent.persistence.sql_repository import SQLStateRepository

class TestEncryption:
    def test_secret_manager_roundtrip(self):
        sm = SecretManager()
        plain = "hello world"
        cipher = sm.encrypt(plain)
        assert cipher != plain
        assert sm.decrypt(cipher) == plain

    def test_secret_manager_custom_key(self):
        # 32 bytes base64 encoded
        key = base64.urlsafe_b64encode(b"1" * 32).decode()
        sm = SecretManager(key=key)
        plain = "test"
        assert sm.decrypt(sm.encrypt(plain)) == plain

    def test_secret_manager_invalid_key_derivation(self):
        # Passing a non-base64 string should trigger derivation
        sm = SecretManager(key="not-a-base64-key")
        plain = "secret"
        assert sm.decrypt(sm.encrypt(plain)) == plain

    def test_sql_repository_webhook_encryption(self):
        repo = SQLStateRepository("sqlite:///:memory:")
        repo.save_webhook({"id": "w1", "project_id": "p1", "action_id": "a", "secret": "plain"})
        
        # Retrieval is decrypted
        assert repo.get_webhook("w1")["secret"] == "plain"
        
        # Database is encrypted
        from gradio_chat_agent.persistence.models import Webhook
        with repo.SessionLocal() as session:
            row = session.get(Webhook, "w1")
            assert row.secret != "plain"

    def test_sql_repository_fallback_for_plain_text(self):
        repo = SQLStateRepository("sqlite:///:memory:")
        # Manually insert plain text into DB (simulating existing data)
        from gradio_chat_agent.persistence.models import Webhook
        with repo.SessionLocal() as session:
            repo._ensure_project("p1")
            session.add(Webhook(id="old", project_id="p1", action_id="a", secret="unencrypted", enabled=True))
            session.commit()
            
        # Should still work
        assert repo.get_webhook("old")["secret"] == "unencrypted"
