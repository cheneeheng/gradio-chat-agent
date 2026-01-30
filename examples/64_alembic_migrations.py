"""Example of using Alembic for database migrations.

This example demonstrates how to:
1. Initialize the database schema using Alembic instead of create_all.
2. Run migrations programmatically (or via CLI).
3. Configure the SQLStateRepository to skip automatic schema creation.
"""

import os
from alembic.config import Config
from alembic import command
from gradio_chat_agent.persistence.sql_repository import SQLStateRepository

def run_example():
    db_url = "sqlite:///example_migrations.db"
    if os.path.exists("example_migrations.db"):
        os.remove("example_migrations.db")

    print(f"--- Scenario: Database Migration Flow ---")

    # 1. Initialize SQLStateRepository WITHOUT auto_create_tables
    # This simulates a production environment where migrations are managed.
    print("Initializing repository with auto_create_tables=False...")
    repo = SQLStateRepository(db_url, auto_create_tables=False)

    # Verify that tables don't exist yet (should fail to query)
    try:
        repo.list_projects()
        print("Error: Tables should not exist yet!")
    except Exception as e:
        print(f"Verified: Database is empty/uninitialized. (Error: {str(e)[:50]}...)")

    # 2. Run migrations programmatically
    print("\nRunning Alembic migrations to 'head'...")
    alembic_cfg = Config("alembic.ini")
    # Override sqlalchemy.url in config to use our example DB
    alembic_cfg.set_main_option("sqlalchemy.url", db_url)
    
    # Run the upgrade command
    command.upgrade(alembic_cfg, "head")
    print("Migrations complete.")

    # 3. Verify that the database is now functional
    print("\nVerifying repository functionality...")
    projects = repo.list_projects()
    print(f"Successfully listed projects. Count: {len(projects)}")
    
    repo.create_project("p1", "Migrated Project")
    projects = repo.list_projects()
    print(f"Project created! New count: {len(projects)}")

    # Cleanup
    if os.path.exists("example_migrations.db"):
        os.remove("example_migrations.db")
    print("\nExample finished and cleaned up.")

if __name__ == "__main__":
    run_example()
