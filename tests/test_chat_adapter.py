import json
from unittest.mock import MagicMock, patch
import pytest

from gradio_chat_agent.chat.openai_adapter import OpenAIAgentAdapter
from gradio_chat_agent.models.intent import ChatIntent
from gradio_chat_agent.models.enums import IntentType
from gradio_chat_agent.models.plan import ExecutionPlan

class TestChatAdapter:
    @pytest.fixture
    def mock_openai_client(self):
        with patch("gradio_chat_agent.chat.openai_adapter.OpenAI") as mock:
            yield mock

    def test_adapter_initialization(self, mock_openai_client):
        adapter = OpenAIAgentAdapter(model_name="test-model")
        assert adapter.model_name == "test-model"
        # Env var override check could be done if we mocked os.environ

    def test_registry_to_tools(self, mock_openai_client):
        adapter = OpenAIAgentAdapter()
        registry = {
            "action.1": {
                "description": "desc",
                "input_schema": {"type": "object"}
            }
        }
        tools = adapter._registry_to_tools(registry)
        
        # Should have action.1 + ask_clarification
        assert len(tools) == 2
        assert tools[0]["function"]["name"] == "action.1"
        assert tools[1]["function"]["name"] == "ask_clarification"

    def test_message_to_intent_action_call(self, mock_openai_client):
        adapter = OpenAIAgentAdapter()
        
        # Mock Response
        mock_completion = MagicMock()
        mock_message = MagicMock()
        mock_tool_call = MagicMock()
        
        mock_tool_call.function.name = "demo.action"
        mock_tool_call.function.arguments = '{"arg": 1}'
        
        mock_message.tool_calls = [mock_tool_call]
        mock_message.content = None
        
        mock_completion.choices = [MagicMock(message=mock_message)]
        
        adapter.client.chat.completions.create.return_value = mock_completion
        
        intent = adapter.message_to_intent_or_plan(
            message="do it",
            history=[{"role": "user", "content": "prev"}], # Added history
            state_snapshot={},
            component_registry={"comp.1": {"description": "d", "permissions": {}}}, # Added component
            action_registry={"demo.action": {}}
        )
        
        assert intent.type == IntentType.ACTION_CALL
        assert intent.action_id == "demo.action"
        assert intent.inputs == {"arg": 1}

    def test_message_to_intent_tool_call_clarification(self, mock_openai_client):
        adapter = OpenAIAgentAdapter()
        
        # Mock Response for clarification tool call
        mock_completion = MagicMock()
        mock_message = MagicMock()
        mock_tool_call = MagicMock()
        
        mock_tool_call.function.name = "ask_clarification"
        mock_tool_call.function.arguments = '{"question": "Why?", "choices": ["A", "B"]}'
        
        mock_message.tool_calls = [mock_tool_call]
        
        mock_completion.choices = [MagicMock(message=mock_message)]
        adapter.client.chat.completions.create.return_value = mock_completion
        
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

    def test_message_to_intent_clarification(self, mock_openai_client):
        adapter = OpenAIAgentAdapter()
        
        # Mock Response (No tools, just text)
        mock_completion = MagicMock()
        mock_message = MagicMock()
        mock_message.tool_calls = None
        mock_message.content = "What do you mean?"
        
        mock_completion.choices = [MagicMock(message=mock_message)]
        adapter.client.chat.completions.create.return_value = mock_completion
        
        intent = adapter.message_to_intent_or_plan(
            message="???",
            history=[],
            state_snapshot={},
            component_registry={},
            action_registry={}
        )
        
        assert intent.type == IntentType.CLARIFICATION_REQUEST
        assert intent.question == "What do you mean?"

    def test_message_to_intent_exception(self, mock_openai_client):
        adapter = OpenAIAgentAdapter()
        adapter.client.chat.completions.create.side_effect = Exception("API Down")
        
        intent = adapter.message_to_intent_or_plan(
            message="hi",
            history=[],
            state_snapshot={},
            component_registry={},
            action_registry={}
        )
        
        assert intent.type == IntentType.CLARIFICATION_REQUEST
        assert "Error communicating" in intent.question

    def test_message_to_intent_with_media(self, mock_openai_client):
        adapter = OpenAIAgentAdapter()
        # Mock successful response
        mock_completion = MagicMock()
        mock_completion.choices = [MagicMock(message=MagicMock(tool_calls=None, content="OK"))]
        adapter.client.chat.completions.create.return_value = mock_completion
        
        adapter.message_to_intent_or_plan(
            message="look at this",
            history=[],
            state_snapshot={},
            component_registry={},
            action_registry={},
            media={"type": "image", "data": "...", "mime_type": "image/png"}
        )
        # Verify call args included media handling logic (which currently passes)
        # Since logic is just 'pass', we mainly ensure it doesn't crash and lines are hit.
        
    def test_message_to_intent_bad_json_args(self, mock_openai_client):
        adapter = OpenAIAgentAdapter()
        
        # Mock Response with bad JSON in arguments
        mock_completion = MagicMock()
        mock_message = MagicMock()
        mock_tool_call = MagicMock()
        
        mock_tool_call.function.name = "demo.action"
        mock_tool_call.function.arguments = '{bad_json'
        
        mock_message.tool_calls = [mock_tool_call]
        mock_completion.choices = [MagicMock(message=mock_message)]
        adapter.client.chat.completions.create.return_value = mock_completion
        
        intent = adapter.message_to_intent_or_plan(
            message="do it",
            history=[],
            state_snapshot={},
            component_registry={},
            action_registry={"demo.action": {}}
        )
        
        # Should fallback to empty dict args and still return action call
        assert intent.type == IntentType.ACTION_CALL
        assert intent.action_id == "demo.action"
        assert intent.inputs == {}

    def test_openai_adapter_multiple_tool_calls(self, mock_openai_client):
        adapter = OpenAIAgentAdapter()
        mock_completion = MagicMock()
        mock_message = MagicMock()
        
        tc1 = MagicMock()
        tc1.id = "1"
        tc1.function.name = "act1"
        tc1.function.arguments = "{}"
        
        tc2 = MagicMock()
        tc2.id = "2"
        tc2.function.name = "act2"
        tc2.function.arguments = "{}"
        
        mock_message.tool_calls = [tc1, tc2]
        mock_completion.choices = [MagicMock(message=mock_message)]
        adapter.client.chat.completions.create.return_value = mock_completion

        res = adapter.message_to_intent_or_plan("msg", [], {}, {}, {"act1": {}, "act2": {}})
        assert isinstance(res, ExecutionPlan)
        assert len(res.steps) == 2

    def test_openai_adapter_hallucination_retry(self, mock_openai_client):
        adapter = OpenAIAgentAdapter()
        
        # 1st response: hallucination
        mock_msg_1 = MagicMock()
        tc_bad = MagicMock()
        tc_bad.id = "bad_call"
        tc_bad.function.name = "hallucinatedaction"
        tc_bad.function.arguments = "{}"
        mock_msg_1.tool_calls = [tc_bad]
        mock_msg_1.role = "assistant"
        mock_msg_1.model_dump.return_value = {"role": "assistant", "tool_calls": [{"id": "bad_call", "function": {"name": "hallucinatedaction", "arguments": "{}"}}]}
        
        # 2nd response: valid
        mock_msg_2 = MagicMock()
        tc_good = MagicMock()
        tc_good.id = "good_call"
        tc_good.function.name = "validaction"
        tc_good.function.arguments = "{}"
        mock_msg_2.tool_calls = [tc_good]
        mock_msg_2.role = "assistant"
        
        mock_completion_1 = MagicMock()
        mock_completion_1.choices = [MagicMock(message=mock_msg_1)]
        
        mock_completion_2 = MagicMock()
        mock_completion_2.choices = [MagicMock(message=mock_msg_2)]
        
        adapter.client.chat.completions.create.side_effect = [mock_completion_1, mock_completion_2]
        
        res = adapter.message_to_intent_or_plan(
            message="do it",
            history=[],
            state_snapshot={},
            component_registry={},
            action_registry={"validaction": {}}
        )
        
        assert isinstance(res, ChatIntent)
        assert res.action_id == "validaction"
        assert adapter.client.chat.completions.create.call_count == 2
