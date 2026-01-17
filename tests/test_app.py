from unittest.mock import patch, MagicMock
import gradio_chat_agent.app as app


class TestApp:
    def test_app_main_import(self):
        assert app.main is not None

    def test_app_main_execution(self):
        with patch("gradio_chat_agent.app.SQLStateRepository") as mock_repo:
            with patch("gradio_chat_agent.app.OpenAIAgentAdapter") as mock_adapter:
                with patch("gradio_chat_agent.app.create_ui") as mock_ui:
                    mock_demo = MagicMock()
                    mock_ui.return_value = mock_demo

                    app.main()

                    mock_repo.assert_called()
                    mock_adapter.assert_called()
                    mock_ui.assert_called()
                    mock_demo.launch.assert_called_with(
                        server_name="0.0.0.0", server_port=7860
                    )

    def test_app_run_as_main(self):
        # Patch launch GLOBALLY to prevent actual server start
        with patch("gradio.Blocks.launch") as mock_launch:
            with patch("gradio_chat_agent.app.SQLStateRepository"), \
                 patch("gradio_chat_agent.app.OpenAIAgentAdapter"), \
                 patch("gradio_chat_agent.app.create_ui") as mock_ui:
                mock_demo = MagicMock()
                mock_ui.return_value = mock_demo
                with patch.dict("os.environ", {"OPENAI_API_KEY": "dummy"}):
                    import runpy
                    runpy.run_path("src/gradio_chat_agent/app.py", run_name="__main__")
                    # Either mock_demo.launch or mock_launch should have been called
                    assert mock_demo.launch.called or mock_launch.called
