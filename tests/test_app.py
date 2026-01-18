from unittest.mock import patch, MagicMock
import gradio_chat_agent.app as app


class TestApp:
    def test_app_main_import(self):
        assert app.main is not None

    def test_app_main_execution(self):
        with patch("gradio_chat_agent.app.SQLStateRepository") as mock_repo:
            with patch("gradio_chat_agent.app.OpenAIAgentAdapter") as mock_adapter:
                with patch("gradio_chat_agent.app.create_ui") as mock_ui:
                    with patch("uvicorn.run") as mock_run:
                        with patch("gradio.mount_gradio_app") as mock_mount:
                            mock_demo = MagicMock()
                            mock_ui.return_value = mock_demo

                            app.main()

                            mock_repo.assert_called()
                            mock_adapter.assert_called()
                            mock_ui.assert_called()
                            mock_mount.assert_called()
                            mock_run.assert_called()
                            args, kwargs = mock_run.call_args
                            assert kwargs["host"] == "0.0.0.0"
                            assert kwargs["port"] == 7860

    def test_app_run_as_main(self):
        # Patch uvicorn.run GLOBALLY to prevent actual server start
        with patch("uvicorn.run") as mock_run:
            with patch("gradio_chat_agent.app.SQLStateRepository"), \
                 patch("gradio_chat_agent.app.OpenAIAgentAdapter"), \
                 patch("gradio.mount_gradio_app"), \
                 patch("gradio_chat_agent.app.create_ui") as mock_ui:
                mock_demo = MagicMock()
                mock_ui.return_value = mock_demo
                with patch.dict("os.environ", {"OPENAI_API_KEY": "dummy"}):
                    import runpy
                    runpy.run_path("src/gradio_chat_agent/app.py", run_name="__main__")
                    assert mock_run.called

    def test_endpoints_via_main(self):
        from fastapi.testclient import TestClient
        
        # We want to capture the 'app' passed to uvicorn.run
        # And we want gr.mount_gradio_app to behave transparently (return the app passed to it)
        with patch("uvicorn.run") as mock_run:
            with patch("gradio_chat_agent.app.SQLStateRepository") as mock_repo_cls:
                mock_repo = mock_repo_cls.return_value
                # Configure repo for health check
                mock_repo.check_health.return_value = True
                
                with patch("gradio_chat_agent.app.OpenAIAgentAdapter"):
                    with patch("gradio_chat_agent.app.create_ui"):
                         # IMPORTANT: Mock mount_gradio_app to return the FIRST argument (the FastAPI app)
                         # otherwise app variable in main() becomes a MagicMock and TestClient won't work well
                         with patch("gradio.mount_gradio_app", side_effect=lambda app, *args, **kwargs: app):
                            app.main()
                            
                            args, kwargs = mock_run.call_args
                            fastapi_app = args[0]
                            
                            client = TestClient(fastapi_app)
                            
                            # Test Health
                            res = client.get("/health")
                            assert res.status_code == 200
                            assert res.json()["status"] == "healthy"
                            
                            # Test Metrics
                            res = client.get("/metrics")
                            assert res.status_code == 200
                            assert "text/plain" in res.headers["content-type"]

                            # Test Unhealthy
                            mock_repo.check_health.return_value = False
                            res = client.get("/health")
                            assert res.status_code == 503
                            assert res.json()["status"] == "unhealthy"
