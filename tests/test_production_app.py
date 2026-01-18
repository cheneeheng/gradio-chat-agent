import pytest
from unittest.mock import patch, MagicMock
from fastapi import FastAPI
from gradio_chat_agent.app import create_app

class TestProductionApp:
    def test_create_app_returns_fastapi_instance(self):
        with patch("gradio_chat_agent.app.SQLStateRepository"), \
             patch("gradio_chat_agent.app.OpenAIAgentAdapter"), \
             patch("gradio_chat_agent.app.create_ui"), \
             patch("gradio.mount_gradio_app", side_effect=lambda app, *args, **kwargs: app):
            
            app = create_app()
            assert isinstance(app, FastAPI)
            assert hasattr(app.state, "scheduler")

    def test_app_lifecycle_events(self):
        with patch("gradio_chat_agent.app.SQLStateRepository"), \
             patch("gradio_chat_agent.app.OpenAIAgentAdapter"), \
             patch("gradio_chat_agent.app.create_ui"), \
             patch("gradio.mount_gradio_app", side_effect=lambda app, *args, **kwargs: app):
            
            app = create_app()
            mock_scheduler = MagicMock()
            app.state.scheduler = mock_scheduler
            
            # Manually trigger events
            # In a real test we might use TestClient with context manager, 
            # but here we want to verify the handlers are attached.
            
            # Find the startup handler
            startup_handlers = [h for h in app.router.on_startup]
            assert len(startup_handlers) > 0
            for handler in startup_handlers:
                handler()
            mock_scheduler.start.assert_called_once()
            
            # Find the shutdown handler
            shutdown_handlers = [h for h in app.router.on_shutdown]
            assert len(shutdown_handlers) > 0
            for handler in shutdown_handlers:
                handler()
            mock_scheduler.stop.assert_called_once()

    def test_main_calls_create_app_and_run(self):
        from gradio_chat_agent.app import main
        with patch("gradio_chat_agent.app.create_app") as mock_create, \
             patch("uvicorn.run") as mock_run:
            
            mock_app = MagicMock()
            mock_create.return_value = mock_app
            
            main()
            
            mock_create.assert_called_once()
            mock_run.assert_called_once_with(mock_app, host="0.0.0.0", port=7860)
