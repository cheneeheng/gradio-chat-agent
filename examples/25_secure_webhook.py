"""Example of Secure Webhook Trigger with HMAC-SHA256.

This example demonstrates:
1. Registering a webhook with a secret.
2. Calculating the HMAC-SHA256 signature for a payload.
3. Triggering the action via the secure webhook endpoint.
"""

import hmac
import hashlib
import json
from gradio_chat_agent.api.endpoints import ApiEndpoints
from gradio_chat_agent.execution.engine import ExecutionEngine
from gradio_chat_agent.persistence.in_memory import InMemoryStateRepository
from gradio_chat_agent.registry.in_memory import InMemoryRegistry
from gradio_chat_agent.registry.demo_actions import counter_component, set_action, set_handler

def run_example():
    # 1. Setup system
    registry = InMemoryRegistry()
    repository = InMemoryStateRepository()
    engine = ExecutionEngine(registry, repository)
    api = ApiEndpoints(engine)
    
    registry.register_component(counter_component)
    registry.register_action(set_action, set_handler)
    
    project_id = "webhook-demo"
    repository.create_project(project_id, "Webhook Demo")
    
    # 2. Register Webhook
    webhook_id = "secure-set-counter"
    webhook_secret = "my-super-secret-key"
    
    repository.save_webhook({
        "id": webhook_id,
        "project_id": project_id,
        "action_id": "demo.counter.set",
        "secret": webhook_secret,
        "enabled": True
    })
    
    print(f"--- Scenario: Triggering Webhook Securely ---")
    
    # 3. Prepare Payload
    payload = {"value": 42}
    payload_json = json.dumps(payload, sort_keys=True)
    
    # 4. Calculate HMAC-SHA256 Signature
    signature = hmac.new(
        webhook_secret.encode("utf-8"),
        payload_json.encode("utf-8"),
        hashlib.sha256
    ).hexdigest()
    
    print(f"Payload: {payload}")
    print(f"Signature: {signature}")
    
    # 5. Execute via API
    response = api.webhook_execute(webhook_id, payload, signature=signature)
    
    print(f"Response Code: {response.get('code')}")
    print(f"Response Message: {response.get('message')}")
    
    # 6. Verify state
    latest = repository.get_latest_snapshot(project_id)
    val = latest.components["demo.counter"]["value"] if latest else 0
    print(f"Counter Value: {val} (Expected: 42)")

if __name__ == "__main__":
    run_example()
