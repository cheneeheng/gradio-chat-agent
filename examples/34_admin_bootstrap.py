"""Example showing how to use and verify the Admin Bootstrap logic.

This script demonstrates how the application automatically creates 
a default admin user if one doesn't exist, and how to disable it.
"""

import os
from unittest.mock import patch
from gradio_chat_agent.persistence.sql_repository import SQLStateRepository
from gradio_chat_agent.app import bootstrap_admin

def run_example():
    db_url = "sqlite:///:memory:"
    
    print("---" + " Scenario 1: Default Bootstrap (Enabled) ---")
    with patch.dict("os.environ", {"ALLOW_DEFAULT_ADMIN": "True"}):
        repo1 = SQLStateRepository(db_url)
        bootstrap_admin(repo1)
        
        user = repo1.get_user("admin")
        if user:
            print(f"Verified: Default admin user created.")
            members = repo1.get_project_members("default_project")
            admin_member = [m for m in members if m["user_id"] == "admin"]
            if admin_member:
                print(f"Verified: Admin added to default project.")
        else:
            print("Failed: Admin user NOT created.")

    print("\n---" + " Scenario 2: Bootstrap Disabled ---")
    # New clean DB
    db_url_2 = "sqlite:///:memory:"
    with patch.dict("os.environ", {"ALLOW_DEFAULT_ADMIN": "False"}):
        repo2 = SQLStateRepository(db_url_2)
        bootstrap_admin(repo2)
        
        user = repo2.get_user("admin")
        if not user:
            print("Verified: Bootstrap skipped as requested.")
        else:
            print("Failed: Admin user created despite being disabled!")

if __name__ == "__main__":
    run_example()
