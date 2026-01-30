"""Example of Secret Encryption for Webhooks.

This example demonstrates how:
1. Webhook secrets are automatically encrypted before being saved to the SQL database.
2. Secrets are decrypted when retrieved via the repository.
3. The raw database contains the cipher text, not the plain text.
"""

from gradio_chat_agent.persistence.sql_repository import SQLStateRepository
from sqlalchemy import select
from gradio_chat_agent.persistence.models import Webhook

def run_example():
    # Use in-memory SQLite for demo
    repo = SQLStateRepository("sqlite:///:memory:")
    
    webhook_id = "secure-webhook"
    plain_secret = "super-sensitive-key-123"
    
    print(f"Saving webhook with secret: {plain_secret}")
    repo.save_webhook({
        "id": webhook_id,
        "project_id": "p1",
        "action_id": "demo.act",
        "secret": plain_secret,
        "enabled": True
    })
    
    # 1. Verify retrieval (Decrypted)
    fetched = repo.get_webhook(webhook_id)
    print(f"Retrieved Secret (Decrypted): {fetched['secret']}")
    assert fetched['secret'] == plain_secret
    
    # 2. Inspect Raw DB (Encrypted)
    with repo.SessionLocal() as session:
        db_row = session.get(Webhook, webhook_id)
        print(f"Raw DB Secret (Cipher Text): {db_row.secret}")
        assert db_row.secret != plain_secret
        assert len(db_row.secret) > len(plain_secret) # Base64/Fernet overhead

    print("\nEncryption and Decryption verified successfully.")

if __name__ == "__main__":
    run_example()
