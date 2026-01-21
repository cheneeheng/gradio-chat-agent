import pytest
from unittest.mock import patch, MagicMock
from fastapi import FastAPI
from gradio_chat_agent.app import create_app


class TestProductionApp:
    def test_create_app_returns_fastapi_instance(self):
        with (
            patch("gradio_chat_agent.app.SQLStateRepository"),
            patch("gradio_chat_agent.app.OpenAIAgentAdapter"),
            patch("gradio_chat_agent.app.create_ui"),
            patch(
                "gradio.mount_gradio_app",
                side_effect=lambda app, *args, **kwargs: app,
            ),
        ):
            app = create_app()
            assert isinstance(app, FastAPI)
            assert hasattr(app.state, "scheduler")

    @pytest.mark.asyncio
    async def test_app_lifecycle_events(self):
        with (
            patch("gradio_chat_agent.app.SQLStateRepository"),
            patch("gradio_chat_agent.app.OpenAIAgentAdapter"),
            patch("gradio_chat_agent.app.create_ui"),
            patch(
                "gradio.mount_gradio_app",
                side_effect=lambda app, *args, **kwargs: app,
            ),
        ):
            app = create_app()

            mock_scheduler = MagicMock()
            mock_observer = MagicMock()
            mock_executor = MagicMock()

            app.state.scheduler = mock_scheduler
            app.state.browser_observer = mock_observer
            app.state.browser_executor = mock_executor

            # Use FastAPI's lifespan context
            lifespan = app.router.lifespan_context(app)

            # ---- Startup ----
            async with lifespan:
                mock_scheduler.start.assert_called_once()
                mock_observer.start.assert_called_once()

            # ---- Shutdown ----
            mock_scheduler.stop.assert_called_once()
            mock_observer.stop.assert_called_once()
            mock_executor.stop.assert_called_once()

    def test_main_calls_create_app_and_run(self):
        from gradio_chat_agent.app import main

        with (
            patch("gradio_chat_agent.app.create_app") as mock_create,
            patch("uvicorn.run") as mock_run,
        ):
            mock_app = MagicMock()
            mock_create.return_value = mock_app

            main()

            mock_create.assert_called_once()
            mock_run.assert_called_once_with(
                mock_app, host="0.0.0.0", port=7860
            )
