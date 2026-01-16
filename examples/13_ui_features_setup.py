"""Example of setting up data for the UI features (Team & Memory).

This example demonstrates:
1. Creating a project for UI demonstration.
2. Adding multiple users with different roles (Admin, Operator, Viewer).
3. Populating Session Memory (Facts) for a specific user.
4. Setting up the database so these appear in the new UI tabs.
"""

import os

from gradio_chat_agent.execution.engine import ExecutionEngine
from gradio_chat_agent.models.enums import ProjectOp
from gradio_chat_agent.persistence.sql_repository import SQLStateRepository
from gradio_chat_agent.registry.in_memory import InMemoryRegistry


def run_example():
    # 1. Setup Persistence
    # Use the same DB as the app (default: sqlite:///gradio_chat_agent.sqlite3)
    db_url = os.environ.get(
        "DATABASE_URL", "sqlite:///gradio_chat_agent.sqlite3"
    )
    print(f"Connecting to database: {db_url}")
    repository = SQLStateRepository(db_url)
    registry = InMemoryRegistry()
    engine = ExecutionEngine(registry, repository)

    project_id = "ui-demo-project"

    # 2. Ensure Project Exists
    # Using the repository directly or via Engine/API.
    # The repository's create_project is simplest for setup scripts.
    if project_id not in repository._ensure_project(project_id) or True:
        # _ensure_project returns void/None in SQL repo usually,
        # but let's use the public API pattern if possible,
        # or just rely on the repository methods directly for setup.
        repository.create_project(project_id, "UI Features Demo")
        print(f"Created/Ensured project: {project_id}")

    # 3. Setup Team Members
    print("\n--- Setting up Team Members ---")
    users = [
        ("admin_user", "admin"),
        ("alice_operator", "operator"),
        ("bob_viewer", "viewer"),
    ]

    for uid, role in users:
        repository.add_project_member(project_id, uid, role)
        print(f"Added member: {uid} as {role}")

    # 4. Setup Session Facts (Memory)
    print("\n--- Setting up Session Facts ---")
    # Facts are scoped to (Project, User)
    target_user = "admin_user"
    facts = {
        "theme_preference": "dark",
        "default_view": "graph",
        "working_directory": "/tmp/demo",
        "notes": "Remember to check the new tabs.",
    }

    for key, val in facts.items():
        repository.save_session_fact(project_id, target_user, key, val)
        print(f"Saved fact for {target_user}: {key}={val}")

    print("\n--- Setup Complete ---")
    print("To view these features:")
    print("1. Run the app: uv run python src/gradio_chat_agent/app.py")
    print(f"2. In the 'Control Panel', ensure Project is '{project_id}'")
    print("   (You may need to add '{project_id}' to the dropdown in layout.py or manually type it if the UI allows)")
    print("3. Check the 'Memory' tab to see the facts.")
    print("4. Check the 'Team' tab to see the members.")


if __name__ == "__main__":
    run_example()
