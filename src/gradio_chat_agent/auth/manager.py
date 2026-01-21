"""Authentication and Session Management for the Gradio Chat Agent.

This module handles OIDC integration and session tracking.
"""

import os
import time
from typing import Optional
from authlib.integrations.starlette_client import OAuth
from authlib.jose import jwt
from starlette.requests import Request
from starlette.middleware.sessions import SessionMiddleware
from fastapi import FastAPI, HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

class AuthManager:
    """Manages OIDC authentication and sessions."""

    def __init__(self, app: FastAPI):
        self.app = app
        self.oauth = OAuth()
        self.bearer_scheme = HTTPBearer(auto_error=False)
        
        # OIDC Configuration
        self.issuer = os.environ.get("OIDC_ISSUER")
        self.client_id = os.environ.get("OIDC_CLIENT_ID")
        self.client_secret = os.environ.get("OIDC_CLIENT_SECRET")
        self.enabled = all([self.issuer, self.client_id, self.client_secret])
        
        self.secret_key = os.environ.get("SESSION_SECRET_KEY", "temporary-secret-key-for-sessions")

        if self.enabled:
            self.oauth.register(
                name="oidc",
                client_id=self.client_id,
                client_secret=self.client_secret,
                server_metadata_url=f"{self.issuer}/.well-known/openid-configuration",
                client_kwargs={"scope": "openid profile email"},
            )
            
            # Add Session Middleware for Authlib/Starlette
            self.app.add_middleware(SessionMiddleware, secret_key=self.secret_key)

    async def login(self, request: Request, redirect_uri: str):
        # ... (same as before)
        if not self.enabled:
            raise HTTPException(
                status_code=status.HTTP_501_NOT_IMPLEMENTED,
                detail="OIDC is not configured."
            )
        return await self.oauth.oidc.authorize_redirect(request, redirect_uri)

    async def auth_callback(self, request: Request):
        # ... (same as before)
        if not self.enabled:
            raise HTTPException(
                status_code=status.HTTP_501_NOT_IMPLEMENTED,
                detail="OIDC is not configured."
            )
        token = await self.oauth.oidc.authorize_access_token(request)
        user = token.get("userinfo")
        if user:
            # Store user info in session
            request.session["user"] = dict(user)
            return user
        return None

    def create_api_token(self, user_id: str) -> str:
        """Creates a signed JWT for API access."""
        header = {"alg": "HS256"}
        payload = {
            "sub": user_id,
            "iat": int(time.time()),
            "exp": int(time.time()) + 3600 * 24 # 24 hours
        }
        return jwt.encode(header, payload, self.secret_key).decode("utf-8")

    def validate_api_token(self, token: str) -> Optional[str]:
        """Validates a JWT and returns the user ID (sub)."""
        try:
            claims = jwt.decode(token, self.secret_key)
            claims.validate()
            return claims.get("sub")
        except Exception:
            return None

    def get_current_user(self, request: Request) -> Optional[dict]:
        """Retrieves the currently authenticated user from session or Bearer token."""
        # 1. Check Session
        user = request.session.get("user")
        if user:
            return user
            
        # 2. Check Bearer Token
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]
            sub = self.validate_api_token(token)
            if sub:
                return {"sub": sub, "name": sub} # Minimal profile
                
        return None

    def logout(self, request: Request):
        """Clears the user session."""
        request.session.pop("user", None)
