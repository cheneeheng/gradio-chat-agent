import os
from unittest.mock import patch, MagicMock
import gradio_chat_agent.app as app

def test_app_respects_env_vars():
    with patch("gradio_chat_agent.app.SQLStateRepository"):
        with patch("gradio_chat_agent.app.OpenAIAgentAdapter"):
            with patch("gradio_chat_agent.app.create_ui"):
                with patch("uvicorn.run") as mock_run:
                    with patch("gradio.mount_gradio_app"):
                        with patch.dict("os.environ", {
                            "GRADIO_SERVER_NAME": "1.2.3.4",
                            "GRADIO_SERVER_PORT": "9999"
                        }):
                            app.main()
                            
                            args, kwargs = mock_run.call_args
                            assert kwargs["host"] == "1.2.3.4"
                            assert kwargs["port"] == 9999

def test_app_uses_defaults():
    with patch("gradio_chat_agent.app.SQLStateRepository"):
        with patch("gradio_chat_agent.app.OpenAIAgentAdapter"):
            with patch("gradio_chat_agent.app.create_ui"):
                with patch("uvicorn.run") as mock_run:
                    with patch("gradio.mount_gradio_app"):
                        # Clear env vars if they exist
                        with patch.dict("os.environ", {}, clear=True):
                            # We still need OPENAI_API_KEY if adapter uses it, but we mocked adapter
                            app.main()
                            
                            args, kwargs = mock_run.call_args
                            assert kwargs["host"] == "0.0.0.0"
                            assert kwargs["port"] == 7860
