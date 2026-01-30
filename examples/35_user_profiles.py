"""Example of using the expanded User Model with Profiles and Orgs.

This example demonstrates how to:
1. Create a user with a full profile (name, email) and organization link.
2. Retrieve and verify these fields.
"""

from gradio_chat_agent.persistence.in_memory import InMemoryStateRepository

def run_example():
    repo = InMemoryStateRepository()
    
    # 1. Create User with Profile
    print("Creating user with profile and organization...")
    repo.create_user(
        user_id="bob_dev",
        password_hash="hashed_pwd",
        full_name="Bob Developer",
        email="bob@example.com",
        organization_id="engineering_dept"
    )
    
    # 2. Retrieve
    user = repo.get_user("bob_dev")
    
    print("\nUser Details:")
    print(f"  ID: {user['id']}")
    print(f"  Name: {user['full_name']}")
    print(f"  Email: {user['email']}")
    print(f"  Org: {user['organization_id']}")
    
    # Verify
    assert user['full_name'] == "Bob Developer"
    assert user['email'] == "bob@example.com"
    assert user['organization_id'] == "engineering_dept"
    print("\nSuccessfully verified all profile fields.")

if __name__ == "__main__":
    run_example()
