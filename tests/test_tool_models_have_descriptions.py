import inspect
from gradio_chat_agent.chat.tools import (
    ProposeActionCall,
    ProposeExecutionPlan,
)


def test_tool_models_have_docstrings():
    assert inspect.getdoc(ProposeActionCall)
    assert inspect.getdoc(ProposeExecutionPlan)


def test_tool_fields_have_descriptions():
    for model in (ProposeActionCall, ProposeExecutionPlan):
        schema = model.model_json_schema()
        props = schema.get("properties", {})
        assert props, "Tool schema must expose properties"
        for name, prop in props.items():
            assert "description" in prop and prop["description"], (
                f"Missing description for field: {model.__name__}.{name}"
            )
