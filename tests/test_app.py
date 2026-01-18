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
