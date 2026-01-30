import os
from unittest.mock import patch
import pytest
from gradio_chat_agent.app import create_app
from gradio_chat_agent.chat.gemini_adapter import GeminiAgentAdapter
from gradio_chat_agent.chat.openai_adapter import OpenAIAgentAdapter

@pytest.fixture
def mock_adapters():
    with patch("gradio_chat_agent.app.GeminiAgentAdapter") as mock_gemini, \
         patch("gradio_chat_agent.app.OpenAIAgentAdapter") as mock_openai, \
         patch("gradio_chat_agent.app.SQLStateRepository") as mock_repo, \
         patch("gradio_chat_agent.app.ExecutionEngine") as mock_engine, \
         patch("gradio_chat_agent.app.create_ui") as mock_ui, \
         patch("gradio_chat_agent.auth.manager.AuthManager") as mock_auth, \
         patch("gradio_chat_agent.app.SchedulerWorker"), \
         patch("gradio_chat_agent.execution.browser_executor.BrowserExecutor"), \
         patch("gradio_chat_agent.execution.observer.AuditLogObserver"), \
         patch("gradio_chat_agent.app.gr.mount_gradio_app"):
        yield mock_gemini, mock_openai

def test_default_adapter_selection(mock_adapters):
    mock_gemini, mock_openai = mock_adapters
    if "LLM_PROVIDER" in os.environ:
        del os.environ["LLM_PROVIDER"]
    
    create_app()
    
    mock_openai.assert_called_once()
    mock_gemini.assert_not_called()

def test_gemini_adapter_selection(mock_adapters):
    mock_gemini, mock_openai = mock_adapters
    os.environ["LLM_PROVIDER"] = "gemini"
    
    try:
        create_app()
        mock_gemini.assert_called_once()
        mock_openai.assert_not_called()
    finally:
        del os.environ["LLM_PROVIDER"]

def test_google_adapter_selection(mock_adapters):
    mock_gemini, mock_openai = mock_adapters
    os.environ["LLM_PROVIDER"] = "google"
    
    try:
        create_app()
        mock_gemini.assert_called_once()
        mock_openai.assert_not_called()
    finally:
        del os.environ["LLM_PROVIDER"]

def test_explicit_openai_adapter_selection(mock_adapters):
    mock_gemini, mock_openai = mock_adapters
    os.environ["LLM_PROVIDER"] = "openai"
    
    try:
        create_app()
        mock_openai.assert_called_once()
        mock_gemini.assert_not_called()
    finally:
        del os.environ["LLM_PROVIDER"]
