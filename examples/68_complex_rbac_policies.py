"""Example of Complex RBAC and Multi-User Authorization.

This example demonstrates:
1. Combining explicit memberships with dynamic role mappings.
2. Handling multiple users with different privileges.
3. How the engine resolves final roles for execution.
"""

from gradio_chat_agent.execution.engine import ExecutionEngine
from gradio_chat_agent.persistence.in_memory import InMemoryStateRepository
from gradio_chat_agent.registry.in_memory import InMemoryRegistry
from gradio_chat_agent.models.action import ActionDeclaration, ActionPermission
from gradio_chat_agent.models.enums import ActionRisk, ActionVisibility, IntentType
from gradio_chat_agent.models.intent import ChatIntent

def setup_system():
    registry = InMemoryRegistry()
    repository = InMemoryStateRepository()
    engine = ExecutionEngine(registry, repository)
    project_id = "rbac-complex-demo"
    repository.create_project(project_id, "Complex RBAC Demo")

    # Define Actions with different risks
    actions = [
        ("demo.read", ActionRisk.LOW),
        ("demo.operate", ActionRisk.MEDIUM),
        ("demo.admin", ActionRisk.HIGH)
    ]
    
    for aid, risk in actions:
        registry.register_action(
            ActionDeclaration(
                action_id=aid, title=aid, description=aid, targets=["t"],
                input_schema={},
                permission=ActionPermission(
                    confirmation_required=(risk == ActionRisk.HIGH),
                    risk=risk, visibility=ActionVisibility.USER
                )
            ),
            handler=lambda i, s: ({}, [], "Success")
        )
    
    # Define Policy with Role Mappings
    policy = {
        "role_mappings": [
            {"role": "operator", "condition": "user.organization_id == 'ops_team'"},
            {"role": "admin", "condition": "user.email.endswith('@company.com') and user.organization_id == 'it_dept'"}
        ]
    }
    repository.set_project_limits(project_id, policy)
    
    # Create Users
    # 1. External Contractor (Viewer)
    repository.create_user("contractor", "h", full_name="John External", organization_id="external")
    
    # 2. Ops Member (Operator by Org)
    repository.create_user("ops_jane", "h", full_name="Jane Ops", organization_id="ops_team")
    
    # 3. IT Admin (Admin by Email + Org)
    repository.create_user("it_bob", "h", full_name="Bob IT", email="bob@company.com", organization_id="it_dept")
    
    # 4. Explicit Project Manager (Admin by Membership)
    repository.create_user("pm_alice", "h", full_name="Alice PM", organization_id="pm_office")
    repository.add_project_member(project_id, "pm_alice", "admin")

    return engine, project_id

def run_example():
    engine, project_id = setup_system()
    
    test_users = ["contractor", "ops_jane", "it_bob", "pm_alice"]
    test_actions = ["demo.read", "demo.operate", "demo.admin"]
    
    print(f"--- RBAC Resolution and Execution Test ---")
    
    for uid in test_users:
        roles = engine.resolve_user_roles(project_id, uid)
        print(f"\nUser: {uid:15} -> Resolved Roles: {roles}")
        
        for aid in test_actions:
            intent = ChatIntent(
                type=IntentType.ACTION_CALL, 
                request_id=f"req-{uid}-{aid}", 
                action_id=aid,
                confirmed=True # Skip confirmation for high-risk to test permissions directly
            )
            
            res = engine.execute_intent(project_id, intent, user_id=uid, user_roles=roles)
            status = "✅ ALLOWED" if res.status == "success" else f"❌ BLOCKED ({res.message})"
            print(f"  Action: {aid:15} -> {status}")

if __name__ == "__main__":
    run_example()
