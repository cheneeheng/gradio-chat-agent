import pytest
from unittest.mock import MagicMock, patch
from gradio_chat_agent.chat.openai_adapter import OpenAIAgentAdapter
from gradio_chat_agent.models.intent import ChatIntent
from gradio_chat_agent.models.enums import IntentType
from gradio_chat_agent.models.plan import ExecutionPlan

@pytest.fixture
def adapter():
    with patch("gradio_chat_agent.chat.openai_adapter.OpenAI"):
        return OpenAIAgentAdapter()

def test_adapter_initialization():
    with patch("gradio_chat_agent.chat.openai_adapter.OpenAI"):
        adapter = OpenAIAgentAdapter(model_name="test-model")
        assert adapter.model_name == "test-model"

def test_registry_to_tools(adapter):
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

def test_message_to_intent_action_call(adapter):
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
        history=[{"role": "user", "content": "prev"}],
        state_snapshot={},
        component_registry={"comp.1": {"description": "d", "permissions": {}}},
        action_registry={"demo.action": {}}
    )
    
    assert intent.type == IntentType.ACTION_CALL
    assert intent.action_id == "demo.action"
    assert intent.inputs == {"arg": 1}

def test_message_to_intent_tool_call_clarification(adapter):
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

def test_message_to_intent_clarification(adapter):
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

def test_message_to_intent_exception(adapter):
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

def test_message_to_intent_with_media(adapter):
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

def test_message_to_intent_bad_json_args(adapter):
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
    
    assert intent.type == IntentType.ACTION_CALL
    assert intent.action_id == "demo.action"
    assert intent.inputs == {}

def test_openai_hallucination_retry(adapter):
    # Mock invalid then valid
    mock_tc_invalid = MagicMock()
    mock_tc_invalid.function.name = "ghost.action"
    mock_tc_invalid.function.arguments = "{}"
    mock_tc_invalid.id = "c1"
    
    mock_msg_invalid = MagicMock()
    mock_msg_invalid.tool_calls = [mock_tc_invalid]
    mock_msg_invalid.content = None
    mock_msg_invalid.role = "assistant"
    mock_msg_invalid.model_dump.return_value = {"role": "assistant", "tool_calls": []}

    mock_tc_valid = MagicMock()
    mock_tc_valid.function.name = "real.action"
    mock_tc_valid.function.arguments = "{}"
    mock_tc_valid.id = "c2"
    
    mock_msg_valid = MagicMock()
    mock_msg_valid.tool_calls = [mock_tc_valid]
    mock_msg_valid.content = None
    mock_msg_valid.role = "assistant"

    adapter.client.chat.completions.create.side_effect = [
        MagicMock(choices=[MagicMock(message=mock_msg_invalid)]),
        MagicMock(choices=[MagicMock(message=mock_msg_valid)])
    ]
    
    res = adapter.message_to_intent_or_plan("do", [], {}, {}, {"real.action": {}})
    assert res.action_id == "real.action"
    assert adapter.client.chat.completions.create.call_count == 2

def test_openai_multimodal_payload(adapter):
    mock_choice = MagicMock()
    mock_choice.message.tool_calls = None
    mock_choice.message.content = "Got it"
    mock_choice.message.role = "assistant"
    adapter.client.chat.completions.create.return_value = MagicMock(choices=[mock_choice])
    
    adapter.message_to_intent_or_plan("look", [], {}, {}, {}, media={"data": "b64", "mime_type": "image/png"})
    
    _, kwargs = adapter.client.chat.completions.create.call_args
    user_msg = kwargs["messages"][-1]
    assert any(p["type"] == "image_url" for p in user_msg["content"])

def test_openai_adapter_errors(adapter):
    adapter.client.chat.completions.create.side_effect = Exception("error")
    res = adapter.message_to_intent_or_plan("hi", [], {}, {}, {})
    assert res.type == IntentType.CLARIFICATION_REQUEST
    assert "error" in res.question

def test_openai_tool_calls_logic(adapter):
    # Clarification
    mock_tc = MagicMock()
    mock_tc.function.name = "ask_clarification"
    mock_tc.function.arguments = '{"question": "which?"}'
    mock_msg = MagicMock(tool_calls=[mock_tc], role="assistant", content=None)
    adapter.client.chat.completions.create.return_value = MagicMock(choices=[MagicMock(message=mock_msg)])
    
    res = adapter.message_to_intent_or_plan("hi", [], {}, {}, {})
    assert res.question == "which?"

    # Empty tool calls
    mock_msg.tool_calls = []
    mock_msg.content = "I can help"
    res = adapter.message_to_intent_or_plan("hi", [], {}, {}, {})
    assert res.question == "I can help"

    # Plan (multiple)
    mock_tc1 = MagicMock(); mock_tc1.function.name = "a.1"; mock_tc1.function.arguments = "{}"
    mock_tc2 = MagicMock(); mock_tc2.function.name = "a.2"; mock_tc2.function.arguments = "{}"
    mock_msg.tool_calls = [mock_tc1, mock_tc2]
    res = adapter.message_to_intent_or_plan("hi", [], {}, {}, {"a.1": {}, "a.2": {}})
    assert isinstance(res, ExecutionPlan)
    assert len(res.steps) == 2
