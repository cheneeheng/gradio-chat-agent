"""Example of OIDC Authentication and JWT Session Management.

This example demonstrates how to:
1. Configure OIDC settings.
2. Generate and validate API Bearer tokens.
3. Simulate an authenticated request.
"""

import os
from fastapi import FastAPI
from gradio_chat_agent.auth.manager import AuthManager
from starlette.requests import Request

def run_example():
    app = FastAPI()
    
    # Configure OIDC (Simulated)
    os.environ["OIDC_ISSUER"] = "https://mock-oidc.com"
    os.environ["OIDC_CLIENT_ID"] = "client-123"
    os.environ["OIDC_CLIENT_SECRET"] = "secret-456"
    os.environ["SESSION_SECRET_KEY"] = "super-secret"

    print("--- Phase 1: Authentication Manager ---")
    auth_manager = AuthManager(app)
    print(f"OIDC Enabled: {auth_manager.enabled}")

    print("\n--- Phase 2: API Token Management ---")
    user_id = "alice_dev"
    token = auth_manager.create_api_token(user_id)
    print(f"Generated JWT for {user_id}: {token[:30]}...")

    # Validate
    sub = auth_manager.validate_api_token(token)
    print(f"Validated token for subject: {sub}")
    assert sub == user_id

    print("\n--- Phase 3: Authenticated Request Simulation ---")
    # Mocking a Starlette Request with Authorization header
    class MockRequest:
        def __init__(self, token):
            self.headers = {"Authorization": f"Bearer {token}"}
            self.session = {} # No session for this test

    mock_req = MockRequest(token)
    user = auth_manager.get_current_user(mock_req)
    print(f"Identified User from Bearer Token: {user}")
    
    # Simulate invalid token
    bad_req = MockRequest("invalid-token")
    user_bad = auth_manager.get_current_user(bad_req)
    print(f"Identified User from Invalid Token: {user_bad}")

    print("\nExample complete.")

if __name__ == "__main__":
    run_example()
