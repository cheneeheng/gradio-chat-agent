"""Example of Webhook with Jinja2 Templating.

This example demonstrates:
1. Registering a webhook with a Jinja2 input template.
2. How the payload is mapped to action inputs using the template.
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
    
    project_id = "jinja-demo"
    repository.create_project(project_id, "Jinja Demo")
    
    # 2. Register Webhook with Jinja2 Template
    # We want to extract 'new_count' from a complex payload and set it to 'value'
    webhook_id = "jinja-set-counter"
    webhook_secret = "secret"
    
    repository.save_webhook({
        "id": webhook_id,
        "project_id": project_id,
        "action_id": "demo.counter.set",
        "secret": webhook_secret,
        "inputs_template": {
            "value": "{{ data.updates[0].new_count }}"
        },
        "enabled": True
    })
    
    print(f"--- Scenario: Complex Payload Mapping with Jinja2 ---")
    
    # 3. Prepare Complex Payload
    payload = {
        "event_type": "state_changed",
        "data": {
            "updates": [
                {"field": "counter", "new_count": "123"}
            ]
        }
    }
    payload_json = json.dumps(payload, sort_keys=True)
    
    # 4. Calculate Signature
    signature = hmac.new(
        webhook_secret.encode("utf-8"),
        payload_json.encode("utf-8"),
        hashlib.sha256
    ).hexdigest()
    
    # 5. Execute
    print(f"Triggering with complex nested payload...")
    api.webhook_execute(webhook_id, payload, signature=signature)
    
    # 6. Verify state (Jinja2 should have extracted '123' and converted to int)
    latest = repository.get_latest_snapshot(project_id)
    val = latest.components["demo.counter"]["value"] if latest else 0
    print(f"Counter Value: {val} (Expected: 123)")

if __name__ == "__main__":
    run_example()
