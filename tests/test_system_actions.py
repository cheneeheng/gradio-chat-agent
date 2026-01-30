from gradio_chat_agent.registry.system_actions import (
    remember_handler, forget_handler, MEMORY_COMPONENT_ID
)
from gradio_chat_agent.models.state_snapshot import StateSnapshot
from gradio_chat_agent.models.execution_result import StateDiffOp

class TestSystemActions:
    def test_remember_handler_new_key(self):
        snapshot = StateSnapshot(snapshot_id="1", components={})
        inputs = {"key": "name", "value": "Alice"}
        
        new_comps, diff, msg = remember_handler(inputs, snapshot)
        
        assert new_comps[MEMORY_COMPONENT_ID]["name"] == "Alice"
        assert len(diff) == 1
        assert diff[0].op == StateDiffOp.ADD
        assert diff[0].path == f"{MEMORY_COMPONENT_ID}.name"
        assert "Alice" in msg

    def test_remember_handler_update_key(self):
        snapshot = StateSnapshot(
            snapshot_id="1", 
            components={MEMORY_COMPONENT_ID: {"name": "Bob"}}
        )
        inputs = {"key": "name", "value": "Alice"}
        
        new_comps, diff, msg = remember_handler(inputs, snapshot)
        
        assert new_comps[MEMORY_COMPONENT_ID]["name"] == "Alice"
        assert len(diff) == 1
        assert diff[0].op == StateDiffOp.REPLACE
        assert "Alice" in msg

    def test_forget_handler_existing(self):
        snapshot = StateSnapshot(
            snapshot_id="1", 
            components={MEMORY_COMPONENT_ID: {"name": "Bob"}}
        )
        inputs = {"key": "name"}
        
        new_comps, diff, msg = forget_handler(inputs, snapshot)
        
        assert "name" not in new_comps[MEMORY_COMPONENT_ID]
        assert len(diff) == 1
        assert diff[0].op == StateDiffOp.REMOVE
        assert "Forgot" in msg

    def test_forget_handler_missing(self):
        snapshot = StateSnapshot(
            snapshot_id="1", 
            components={MEMORY_COMPONENT_ID: {}}
        )
        inputs = {"key": "name"}
        
        new_comps, diff, msg = forget_handler(inputs, snapshot)
        
        assert "name" not in new_comps[MEMORY_COMPONENT_ID]
        assert len(diff) == 0
        assert "Key not found" in msg
