import pytest
import os
from unittest.mock import MagicMock, AsyncMock, patch
from fastapi import FastAPI
from starlette.requests import Request
from gradio_chat_agent.auth.manager import AuthManager

class TestAuthManager:
    @pytest.fixture
    def app(self):
        return FastAPI()

    def test_auth_manager_disabled_by_default(self, app):
        with pytest.MonkeyPatch().context() as m:
            m.delenv("OIDC_ISSUER", raising=False)
            auth = AuthManager(app)
            assert auth.enabled is False

    def test_auth_manager_enabled_with_env(self, app):
        with pytest.MonkeyPatch().context() as m:
            m.setenv("OIDC_ISSUER", "https://issuer")
            m.setenv("OIDC_CLIENT_ID", "id")
            m.setenv("OIDC_CLIENT_SECRET", "secret")
            auth = AuthManager(app)
            assert auth.enabled is True

    def test_jwt_lifecycle(self, app):
        auth = AuthManager(app)
        user_id = "test_user"
        token = auth.create_api_token(user_id)
        
        # Validate
        assert auth.validate_api_token(token) == user_id
        
        # Invalid token
        assert auth.validate_api_token("bad.token.val") is None

    def test_get_current_user_session(self, app):
        auth = AuthManager(app)
        class MockRequest:
            def __init__(self, session):
                self.session = session
                self.headers = {}
        
        req = MockRequest({"user": {"name": "Bob"}})
        assert auth.get_current_user(req) == {"name": "Bob"}

    def test_get_current_user_bearer(self, app):
        auth = AuthManager(app)
        token = auth.create_api_token("alice")
        
        class MockRequest:
            def __init__(self, token):
                self.headers = {"Authorization": f"Bearer {token}"}
                self.session = {}
        
        req = MockRequest(token)
        user = auth.get_current_user(req)
        assert user["sub"] == "alice"

    def test_logout(self, app):
        auth = AuthManager(app)
        class MockRequest:
            def __init__(self, session):
                self.session = session
        req = MockRequest({"user": "data"})
        auth.logout(req)
        assert "user" not in req.session

    @pytest.mark.asyncio
    async def test_oidc_methods_raise_if_disabled(self, app):
        auth = AuthManager(app)
        auth.enabled = False
        
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc:
            await auth.login(None, "/")
        assert exc.value.status_code == 501
        
        with pytest.raises(HTTPException) as exc:
            await auth.auth_callback(None)
        assert exc.value.status_code == 501

    @pytest.mark.asyncio
    async def test_auth_manager_oidc_coverage(self, app):
        with patch.dict("os.environ", {
            "OIDC_ISSUER": "https://issuer",
            "OIDC_CLIENT_ID": "id",
            "OIDC_CLIENT_SECRET": "secret"
        }):
            auth = AuthManager(app)
            assert auth.enabled is True
            
            # 1. Test login redirect
            mock_req = MagicMock(spec=Request)
            auth.oauth.oidc.authorize_redirect = AsyncMock(return_value="redirect")
            res = await auth.login(mock_req, "https://callback")
            assert res == "redirect"
            
            # 2. Test auth_callback
            # Success
            auth.oauth.oidc.authorize_access_token = AsyncMock(return_value={
                "userinfo": {"sub": "u1", "name": "User 1"}
            })
            mock_req.session = {}
            user = await auth.auth_callback(mock_req)
            assert user["sub"] == "u1"
            assert mock_req.session["user"]["sub"] == "u1"

            # Failure
            auth.oauth.oidc.authorize_access_token = AsyncMock(return_value={})
            user = await auth.auth_callback(mock_req)
            assert user is None

            # 3. Test get_current_user returns None
            mock_req.session = {}
            mock_req.headers = {}
            assert auth.get_current_user(mock_req) is None

            # 4. Test logout
            mock_req.session = {"user": "data"}
            auth.logout(mock_req)
            assert "user" not in mock_req.session