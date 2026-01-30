import pytest
from unittest.mock import MagicMock, patch
from gradio_chat_agent.chat.gemini_adapter import GeminiAgentAdapter
from gradio_chat_agent.models.intent import ChatIntent
from gradio_chat_agent.models.enums import IntentType
from gradio_chat_agent.models.plan import ExecutionPlan
import google.generativeai as genai

@pytest.fixture
def mock_genai():
    with patch("gradio_chat_agent.chat.gemini_adapter.genai") as mock:
        yield mock

@pytest.fixture
def adapter(mock_genai):
    return GeminiAgentAdapter()


class TestGeminiAgentAdapter:
    def test_adapter_initialization(self, mock_genai):
        adapter = GeminiAgentAdapter(model_name="test-gemini")
        assert adapter.model_name == "test-gemini"
        mock_genai.configure.assert_called_once()

    def test_registry_to_tools(self, adapter):
        registry = {
            "action.1": {
                "description": "desc",
                "input_schema": {"type": "object"}
            }
        }
        tool = adapter._registry_to_tools(registry)
        
        # Check if function declarations are correct
        # tool is a Tool object with function_declarations
        declarations = tool.function_declarations
        assert len(declarations) == 2
        assert declarations[0].name == "action.1"
        assert declarations[1].name == "ask_clarification"

    def test_message_to_intent_action_call(self, adapter, mock_genai):
        # Mock Response
        mock_response = MagicMock()
        mock_part = MagicMock()
        mock_fn = MagicMock()
        mock_fn.name = "demo.action"
        mock_fn.args = {"arg": 1}
        mock_part.function_call = mock_fn
        mock_part.text = None
        
        mock_response.parts = [mock_part]
        mock_response.usage_metadata.total_token_count = 10
        
        # Mock Chat Session
        mock_chat = MagicMock()
        mock_chat.send_message.return_value = mock_response
        
        mock_model = MagicMock()
        mock_model.start_chat.return_value = mock_chat
        mock_genai.GenerativeModel.return_value = mock_model
        
        intent = adapter.message_to_intent_or_plan(
            message="do it",
            history=[{"role": "user", "content": "prev"}],
            state_snapshot={},
            component_registry={"comp.1": {"description": "d", "permissions": {}}},
            action_registry={"demo.action": {}}
        )
        
        assert intent.type == IntentType.ACTION_CALL
        assert intent.action_id == "demo.action"
        assert intent.inputs == {"arg": 1}

    def test_message_to_intent_clarification_tool(self, adapter, mock_genai):
        # Mock Response for clarification tool call
        mock_response = MagicMock()
        mock_part = MagicMock()
        mock_fn = MagicMock()
        mock_fn.name = "ask_clarification"
        mock_fn.args = {"question": "Why?", "choices": ["A", "B"]}
        mock_part.function_call = mock_fn
        mock_part.text = None
        
        mock_response.parts = [mock_part]
        mock_response.usage_metadata.total_token_count = 5

        mock_chat = MagicMock()
        mock_chat.send_message.return_value = mock_response
        
        mock_model = MagicMock()
        mock_model.start_chat.return_value = mock_chat
        mock_genai.GenerativeModel.return_value = mock_model
        
        intent = adapter.message_to_intent_or_plan(
            message="ambiguous",
            history=[],
            state_snapshot={},
            component_registry={},
            action_registry={}
        )
        
        assert intent.type == IntentType.CLARIFICATION_REQUEST
        assert intent.question == "Why?"
        assert intent.choices == ["A", "B"]

    def test_message_to_intent_text_fallback(self, adapter, mock_genai):
        # Mock Response (No tools, just text)
        mock_response = MagicMock()
        mock_part = MagicMock()
        mock_part.function_call = None
        
        # Simulate text response via parts or text property
        # The adapter checks `response.parts` then `response.text` if no function call in parts
        # If parts has no function call, it uses response.text
        
        # We need parts to be iterable but contain no function calls
        mock_part.function_call = None
        mock_response.parts = [mock_part]
        mock_response.text = "What do you mean?"
        mock_response.usage_metadata.total_token_count = 5

        mock_chat = MagicMock()
        mock_chat.send_message.return_value = mock_response
        
        mock_model = MagicMock()
        mock_model.start_chat.return_value = mock_chat
        mock_genai.GenerativeModel.return_value = mock_model
        
        intent = adapter.message_to_intent_or_plan(
            message="???",
            history=[],
            state_snapshot={},
            component_registry={},
            action_registry={}
        )
        
        assert intent.type == IntentType.CLARIFICATION_REQUEST
        assert intent.question == "What do you mean?"

    def test_message_to_intent_exception(self, adapter, mock_genai):
        mock_model = MagicMock()
        mock_model.start_chat.side_effect = Exception("API Down")
        mock_genai.GenerativeModel.return_value = mock_model
        
        intent = adapter.message_to_intent_or_plan(
            message="hi",
            history=[],
            state_snapshot={},
            component_registry={},
            action_registry={}
        )
        
        assert intent.type == IntentType.CLARIFICATION_REQUEST
        assert "Error communicating" in intent.question

    def test_message_to_intent_unknown_action(self, adapter, mock_genai):
        # Mock Response with unknown action
        mock_response = MagicMock()
        mock_part = MagicMock()
        mock_fn = MagicMock()
        mock_fn.name = "unknown.action"
        mock_fn.args = {}
        mock_part.function_call = mock_fn
        mock_response.parts = [mock_part]
        mock_response.usage_metadata.total_token_count = 5
        
        mock_chat = MagicMock()
        mock_chat.send_message.return_value = mock_response
        
        mock_model = MagicMock()
        mock_model.start_chat.return_value = mock_chat
        mock_genai.GenerativeModel.return_value = mock_model
        
        intent = adapter.message_to_intent_or_plan(
            message="do unknown",
            history=[],
            state_snapshot={},
            component_registry={},
            action_registry={"known.action": {}}
        )
        
        assert intent.type == IntentType.CLARIFICATION_REQUEST
        assert "unknown action" in intent.question

    def test_message_to_intent_multimodal(self, adapter, mock_genai):
        mock_response = MagicMock()
        mock_response.parts = []
        mock_response.text = "OK"
        
        mock_chat = MagicMock()
        mock_chat.send_message.return_value = mock_response
        mock_model = MagicMock()
        mock_model.start_chat.return_value = mock_chat
        mock_genai.GenerativeModel.return_value = mock_model
        
        adapter.message_to_intent_or_plan(
            message="look",
            history=[],
            state_snapshot={},
            component_registry={},
            action_registry={},
            media={"data": "b64", "mime_type": "image/png"}
        )
        
        # Check that user_parts contained the blob
        args, _ = mock_chat.send_message.call_args
        user_parts = args[0]
        assert len(user_parts) == 2
        assert isinstance(user_parts[1], dict)
        assert user_parts[1]["mime_type"] == "image/png"
