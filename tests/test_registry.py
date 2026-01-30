from gradio_chat_agent.models.action import (
    ActionDeclaration,
    ActionPermission,
)
from gradio_chat_agent.models.component import (
    ComponentDeclaration,
    ComponentPermissions,
)
from gradio_chat_agent.models.enums import ActionRisk, ActionVisibility
from gradio_chat_agent.registry.in_memory import InMemoryRegistry


class TestRegistry:
    def test_component_registration(self):
        registry = InMemoryRegistry()
        comp = ComponentDeclaration(
            component_id="c1",
            title="C1",
            description="D1",
            state_schema={},
            permissions=ComponentPermissions(readable=True),
        )
        registry.register_component(comp)
        assert registry.get_component("c1") == comp
        assert len(registry.list_components()) == 1

    def test_action_registration(self):
        registry = InMemoryRegistry()
        action = ActionDeclaration(
            action_id="a1",
            title="A1",
            description="D1",
            targets=["c1"],
            input_schema={},
            permission=ActionPermission(
                confirmation_required=False,
                risk=ActionRisk.LOW,
                visibility=ActionVisibility.USER,
            ),
        )

        def handler(inputs, snapshot):
            return {}, [], "ok"

        registry.register_action(action, handler)
        assert registry.get_action("a1") == action
        assert registry.get_handler("a1") == handler
        assert len(registry.list_actions()) == 1
