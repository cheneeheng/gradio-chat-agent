import pytest
import gradio as gr
from gradio_chat_agent.ui.binder import UIBinder


class TestUIBinder:
    def test_bind_and_get_components(self):
        binder = UIBinder()
        c1 = gr.Slider()
        c2 = gr.Checkbox()
        
        binder.bind("a.b", c1)
        binder.bind("x.y", c2)
        
        components = binder.get_bound_components()
        assert len(components) == 2
        assert components[0] == c1
        assert components[1] == c2

    def test_get_value_at_path(self):
        binder = UIBinder()
        state = {"a": {"b": {"c": 42}}, "x": 10}
        
        assert binder._get_value_at_path(state, "a.b.c") == 42
        assert binder._get_value_at_path(state, "x") == 10
        assert binder._get_value_at_path(state, "a.b.missing") is None
        assert binder._get_value_at_path(state, "missing.path") is None
        assert binder._get_value_at_path(state, "a.b.c.too.deep") is None

    def test_get_updates_success(self):
        binder = UIBinder()
        c1 = gr.Slider()
        c2 = gr.Textbox()
        
        binder.bind("counter.val", c1)
        binder.bind("user.name", c2, update_fn=lambda x: f"Hi {x}")
        
        state = {"counter": {"val": 10}, "user": {"name": "Bob"}}
        
        updates = binder.get_updates(state)
        
        assert len(updates) == 2
        assert updates[0]["value"] == 10
        assert updates[1]["value"] == "Hi Bob"

    def test_get_updates_missing_path(self):
        binder = UIBinder()
        c1 = gr.Slider()
        binder.bind("missing.path", c1)
        
        state = {"something": "else"}
        
        updates = binder.get_updates(state)
        
        assert len(updates) == 1
        # Should return an empty gr.update() which doesn't have a 'value' key if not set
        assert "value" not in updates[0]

    def test_get_updates_not_a_dict(self):
        binder = UIBinder()
        c1 = gr.Slider()
        binder.bind("a.b", c1)
        
        state = {"a": "not_a_dict"}
        
        updates = binder.get_updates(state)
        assert len(updates) == 1
        assert "value" not in updates[0]
