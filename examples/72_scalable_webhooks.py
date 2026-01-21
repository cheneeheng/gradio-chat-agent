"""Example of Scalable Webhooks with Background Processing.

This example demonstrates how to:
1. Configure a webhook.
2. Trigger the webhook via the API with `use_huey=True`.
3. Observe the action being queued for asynchronous background execution.
"""

import hmac
import hashlib
import json
import os
from gradio_chat_agent.api.endpoints import ApiEndpoints
from gradio_chat_agent.execution.engine import ExecutionEngine
from gradio_chat_agent.persistence.in_memory import InMemoryStateRepository
from gradio_chat_agent.registry.in_memory import InMemoryRegistry
from gradio_chat_agent.registry.demo_actions import counter_component, set_action, set_handler
from gradio_chat_agent.execution.tasks import huey

def run_example():
    # 1. Setup system
    registry = InMemoryRegistry()
    repository = InMemoryStateRepository()
    engine = ExecutionEngine(registry, repository)
    api = ApiEndpoints(engine)
    
    registry.register_component(counter_component)
    registry.register_action(set_action, set_handler)
    
    project_id = "scalable-webhook-demo"
    repository.create_project(project_id, "Scalable Webhook Demo")
    
    # 2. Register Webhook
    webhook_id = "bg-set-counter"
    webhook_secret = "secret-key"
    
    repository.save_webhook({
        "id": webhook_id,
        "project_id": project_id,
        "action_id": "demo.counter.set",
        "secret": webhook_secret,
        "enabled": True
    })
    
    print(f"--- Scenario: Triggering Webhook with Background Offloading ---")
    
    # 3. Prepare Payload and Signature
    payload = {"value": 99}
    payload_json = json.dumps(payload, sort_keys=True)
    signature = hmac.new(
        webhook_secret.encode("utf-8"),
        payload_json.encode("utf-8"),
        hashlib.sha256
    ).hexdigest()
    
    # 4. Execute via API with use_huey=True
    # This simulates a high-traffic scenario where we don't want to wait for execution
    print(f"Executing webhook {webhook_id} with use_huey=True...")
    response = api.webhook_execute(
        webhook_id, 
        payload, 
        signature=signature, 
        use_huey=True
    )
    
    print(f"API Response Code: {response.get('code')}")
    print(f"API Response Message: {response.get('message')}")
    print(f"API Data: {response.get('data')}")
    
    # 5. Verify Huey Queue
    pending = huey.pending()
    print(f"\nTasks pending in Huey queue: {len(pending)}")
    if pending:
        task = pending[0]
        print(f"  - Queued Task ID: {task.id}")
        print(f"  - Action ID: {task.args[1]}") # From execute_background_action signature
        print(f"  - Project ID: {task.args[0]}")
        
        print("\nSUCCESS: Webhook execution successfully offloaded to background worker.")
    else:
        print("\nFAILURE: No tasks found in Huey queue.")

if __name__ == "__main__":
    run_example()
