"""Example of using the User Model and Persistence.

This example demonstrates how to:
1. Create a new user in the repository.
2. Retrieve user details by ID.
3. Update a user's password.
"""

from gradio_chat_agent.persistence.in_memory import InMemoryStateRepository

def run_example():
    repo = InMemoryStateRepository()
    
    username = "alice"
    initial_hash = "hash_v1"
    
    # 1. Create User
    print(f"Creating user: {username}")
    repo.create_user(username, initial_hash)
    
    # 2. Get User
    user = repo.get_user(username)
    if user:
        print(f"User found: {user['id']} (Hash: {user['password_hash']})")
    else:
        print("User not found!")

    # 3. Update Password
    new_hash = "hash_v2"
    print(f"Updating password for: {username}")
    repo.update_user_password(username, new_hash)
    
    # 4. Verify Update
    updated_user = repo.get_user(username)
    print(f"Updated Hash: {updated_user['password_hash']}")

if __name__ == "__main__":
    run_example()
