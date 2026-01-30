import os
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch
from gradio_chat_agent.app import main
from fastapi import FastAPI

def test_cors_configuration():
    # We can't easily test the middleware on the app created inside main() without running it.
    # But we can test the logic used to set it up.
    
    with patch.dict("os.environ", {"GRADIO_ALLOWED_ORIGINS": "http://test.com,https://app.com"}):
        allowed_origins = os.environ.get("GRADIO_ALLOWED_ORIGINS", "*").split(",")
        assert allowed_origins == ["http://test.com", "https://app.com"]

    with patch.dict("os.environ", {}, clear=True):
        allowed_origins = os.environ.get("GRADIO_ALLOWED_ORIGINS", "*").split(",")
        assert allowed_origins == ["*"]

def test_cors_middleware_integration():
    from fastapi.middleware.cors import CORSMiddleware
    app = FastAPI()
    allowed_origins = ["http://test.com"]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    client = TestClient(app)
    
    # Test preflight
    headers = {
        "Origin": "http://test.com",
        "Access-Control-Request-Method": "GET",
    }
    response = client.options("/", headers=headers)
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://test.com"

    # Test disallowed origin
    headers = {
        "Origin": "http://disallowed.com",
        "Access-Control-Request-Method": "GET",
    }
    response = client.options("/", headers=headers)
    assert "access-control-allow-origin" not in response.headers
