"""Example of Policy Templating for new projects.

This example demonstrates how:
1. Creating a project via the API automatically applies a default policy.
2. The default policy includes rate limits and budget.
"""

from gradio_chat_agent.api.endpoints import ApiEndpoints
from gradio_chat_agent.execution.engine import ExecutionEngine
from gradio_chat_agent.persistence.in_memory import InMemoryStateRepository
from gradio_chat_agent.registry.in_memory import InMemoryRegistry
from gradio_chat_agent.models.enums import ProjectOp

def run_example():
    repo = InMemoryStateRepository()
    api = ApiEndpoints(ExecutionEngine(InMemoryRegistry(), repo))
    
    print("Creating a new project...")
    res = api.manage_project(ProjectOp.CREATE, name="Template Demo", user_id="admin")
    
    project_id = res["data"]["project_id"]
    print(f"Project Created: {project_id}")
    
    # Verify Policy
    policy = repo.get_project_limits(project_id)
    print("\nApplied Default Policy:")
    import json
    print(json.dumps(policy, indent=2))
    
    assert "limits" in policy
    assert policy["limits"]["rate"]["per_minute"] == 10

if __name__ == "__main__":
    run_example()
