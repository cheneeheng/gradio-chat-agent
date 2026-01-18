"""Example of Webhook Secret Rotation.

This example demonstrates how to:
1. Create a webhook with an initial secret.
2. Use the rotate_webhook_secret API to update the secret.
3. Verify that the new secret is required for execution.
"""

from gradio_chat_agent.api.endpoints import ApiEndpoints
from gradio_chat_agent.execution.engine import ExecutionEngine
from gradio_chat_agent.persistence.in_memory import InMemoryStateRepository
from gradio_chat_agent.registry.in_memory import InMemoryRegistry
from gradio_chat_agent.models.enums import WebhookOp

def run_example():
    # 1. Setup
    repo = InMemoryStateRepository()
    engine = ExecutionEngine(InMemoryRegistry(), repo)
    api = ApiEndpoints(engine)
    
    project_id = "rotation-demo"
    webhook_id = "wh-123"
    initial_secret = "initial-secret"
    
    # Create webhook
    config = {
        "id": webhook_id,
        "project_id": project_id,
        "action_id": "demo.act",
        "secret": initial_secret,
        "enabled": True
    }
    api.manage_webhook(WebhookOp.CREATE, config=config)
    print(f"Webhook created with secret: {initial_secret}")
    
    # 2. Rotate Secret
    print("\n--- Rotating Secret ---")
    new_secret = "super-secure-new-secret"
    res = api.rotate_webhook_secret(webhook_id, new_secret=new_secret)
    print(f"API Message: {res['message']}")
    print(f"New Secret from API: {res['data']['new_secret']}")
    
    # 3. Verify in Repo
    webhook = repo.get_webhook(webhook_id)
    print(f"Secret in Repository: {webhook['secret']}")
    assert webhook['secret'] == new_secret
    
    # 4. Generate random secret
    print("\n--- Rotating to random secret ---")
    res2 = api.rotate_webhook_secret(webhook_id)
    print(f"Random Secret generated: {res2['data']['new_secret']}")
    
    webhook2 = repo.get_webhook(webhook_id)
    assert webhook2['secret'] == res2['data']['new_secret']
    print("Secret rotation verified.")

if __name__ == "__main__":
    run_example()
