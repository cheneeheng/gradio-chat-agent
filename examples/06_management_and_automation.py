"""Example of Project Management, Webhooks, and Schedules.

This example demonstrates how to use the management endpoints to:
1. Programmatically create and manage projects.
2. Manage user memberships and roles.
3. Configure webhooks for external triggers.
4. Set up automated execution schedules.
5. Apply governance policies dynamically.
"""

import uuid

from gradio_chat_agent.api.endpoints import ApiEndpoints
from gradio_chat_agent.execution.engine import ExecutionEngine
from gradio_chat_agent.models.enums import (
    MembershipOp,
    ProjectOp,
    ScheduleOp,
    WebhookOp,
)
from gradio_chat_agent.persistence.in_memory import InMemoryStateRepository
from gradio_chat_agent.registry.demo_actions import (
    counter_component,
    set_action,
    set_handler,
)
from gradio_chat_agent.registry.in_memory import InMemoryRegistry


def run_example():
    # 1. Initialize System
    print("--- Initializing System ---")
    registry = InMemoryRegistry()
    repository = InMemoryStateRepository()
    engine = ExecutionEngine(registry, repository)
    api = ApiEndpoints(engine)

    # Register demo components
    registry.register_component(counter_component)
    registry.register_action(set_action, set_handler)

    # 2. Project Lifecycle Management
    print("\n--- Project Lifecycle ---")
    project_id = f"proj-{uuid.uuid4().hex[:8]}"

    # Create Project (System Admin required)
    print(f"Creating project: {project_id}")
    res = api.manage_project(
        ProjectOp.CREATE, name="Automation Demo", project_id=project_id, user_id="admin"
    )
    print(f"Result: {res}")

    # 3. Membership Management
    print("\n--- Membership Management ---")
    user_alice = "alice"
    user_bob = "bob"

    # Add Alice as Admin
    print(f"Adding {user_alice} as Admin...")
    res = api.manage_membership(
        MembershipOp.ADD, project_id, user_alice, role="admin"
    )
    print(f"Result: {res}")

    # Add Bob as Viewer
    print(f"Adding {user_bob} as Viewer...")
    res = api.manage_membership(
        MembershipOp.ADD, project_id, user_bob, role="viewer"
    )
    print(f"Result: {res}")

    # Update Bob to Operator
    print(f"Promoting {user_bob} to Operator...")
    res = api.manage_membership(
        MembershipOp.UPDATE_ROLE, project_id, user_bob, role="operator"
    )
    print(f"Result: {res}")

    # 4. Webhook Configuration
    print("\n--- Webhook Configuration ---")
    webhook_id = f"wh-{uuid.uuid4().hex[:8]}"
    webhook_secret = "super-secret-key"

    webhook_config = {
        "id": webhook_id,
        "project_id": project_id,
        "action_id": "demo.counter.set",
        "secret": webhook_secret,
        "inputs_template": {"value": "{{ payload_value }}"},
        "enabled": True,
    }

    print(f"Creating Webhook: {webhook_id}")
    res = api.manage_webhook(WebhookOp.CREATE, config=webhook_config)
    print(f"Result: {res}")

    # Simulate Webhook Trigger with correct HMAC signature
    print("Simulating external webhook trigger...")
    payload = {"payload_value": 100}
    
    import hmac
    import hashlib
    import json
    payload_json = json.dumps(payload, sort_keys=True)
    signature = hmac.new(
        webhook_secret.encode("utf-8"),
        payload_json.encode("utf-8"),
        hashlib.sha256
    ).hexdigest()

    res = api.webhook_execute(webhook_id, payload, signature=signature)
    print(
        f"Webhook Execution Result: {res.get('status')} - {res.get('message')}"
    )

    # Verify state
    snapshot = repository.get_latest_snapshot(project_id)
    assert snapshot is not None
    val = snapshot.components["demo.counter"]["value"]
    print(f"Counter State after webhook: {val}")

    # 5. Schedule Configuration
    print("\n--- Schedule Configuration ---")
    schedule_id = f"sch-{uuid.uuid4().hex[:8]}"

    schedule_config = {
        "id": schedule_id,
        "project_id": project_id,
        "action_id": "demo.counter.set",
        "cron": "0 0 * * *",  # Daily at midnight
        "inputs": {"value": 0},  # Reset to 0
        "enabled": True,
    }

    print(f"Creating Schedule: {schedule_id}")
    res = api.manage_schedule(ScheduleOp.CREATE, config=schedule_config)
    print(f"Result: {res}")

    # 6. Policy Updates
    print("\n--- Policy Management ---")
    print("Updating project limits...")
    new_policy = {
        "limits": {"rate": {"per_minute": 5}, "budget": {"daily": 100}}
    }
    res = api.update_project_policy(project_id, new_policy)
    print(f"Result: {res}")

    limits = repository.get_project_limits(project_id)
    print(
        f"Verified Limits: Rate={limits['limits']['rate']['per_minute']}/min"
    )

    # 7. Cleanup
    print("\n--- Cleanup ---")
    print("Purging project (Requires confirmation)...")
    res = api.manage_project(ProjectOp.PURGE, project_id=project_id, user_id="admin", confirmed=True)
    print(f"Result: {res}")

    # Verify purge
    snaps = repository.get_latest_snapshot(project_id)
    print(f"Snapshot exists after purge? {snaps is not None}")


if __name__ == "__main__":
    run_example()
