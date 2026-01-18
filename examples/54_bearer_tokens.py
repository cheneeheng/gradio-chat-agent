"""Example of API Bearer Token Lifecycle.

This example demonstrates how to:
1. Create a new API token for a user (as a system admin).
2. List active tokens.
3. Validate a token.
4. Revoke a token and verify it is no longer valid.
"""

from gradio_chat_agent.api.endpoints import ApiEndpoints
from gradio_chat_agent.execution.engine import ExecutionEngine
from gradio_chat_agent.persistence.in_memory import InMemoryStateRepository
from gradio_chat_agent.registry.in_memory import InMemoryRegistry

def run_example():
    # 1. Setup
    repo = InMemoryStateRepository()
    engine = ExecutionEngine(InMemoryRegistry(), repo)
    api = ApiEndpoints(engine)
    
    owner_id = "alice"
    repo.create_user(owner_id, "hash")
    
    print(f"--- Creating API Token for {owner_id} ---")
    res = api.create_api_token(owner_id, "Dev Token", user_id="admin", expires_in_days=30)
    token_val = res["data"]["token"]
    print(f"Generated Token: {token_val}")
    print(f"Expires at: {res['data']['expires_at']}")
    
    # 2. List Tokens
    print("\n--- Listing Tokens ---")
    tokens_res = api.list_api_tokens(owner_id, user_id="admin")
    for t in tokens_res["data"]:
        print(f"ID: {t['id']}, Name: {t['name']}")
        
    # 3. Validate Token
    print("\n--- Validating Token ---")
    user_id = repo.validate_api_token(token_val)
    print(f"Token owner: {user_id}")
    assert user_id == owner_id
    
    # 4. Revoke Token
    print("\n--- Revoking Token ---")
    api.revoke_api_token(token_val, user_id="admin")
    
    # 5. Verify Revocation
    user_id_after = repo.validate_api_token(token_val)
    print(f"Validation after revocation: {user_id_after}")
    assert user_id_after is None
    print("Token lifecycle verified.")

if __name__ == "__main__":
    run_example()
