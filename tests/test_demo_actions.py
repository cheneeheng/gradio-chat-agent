from gradio_chat_agent.registry.demo_actions import (
    set_handler, increment_handler, reset_handler, COUNTER_ID
)
from gradio_chat_agent.models.state_snapshot import StateSnapshot
from gradio_chat_agent.models.execution_result import StateDiffOp

class TestDemoActions:
    def test_set_handler(self):
        snapshot = StateSnapshot(snapshot_id="1", components={})
        inputs = {"value": 42}
        new_comps, diff, msg = set_handler(inputs, snapshot)
        
        assert new_comps[COUNTER_ID]["value"] == 42
        assert diff[0].value == 42

    def test_increment_handler_default(self):
        snapshot = StateSnapshot(snapshot_id="1", components={COUNTER_ID: {"value": 10}})
        inputs = {} # default amount=1
        new_comps, diff, msg = increment_handler(inputs, snapshot)
        
        assert new_comps[COUNTER_ID]["value"] == 11
        assert diff[0].value == 11

    def test_increment_handler_custom(self):
        snapshot = StateSnapshot(snapshot_id="1", components={COUNTER_ID: {"value": 10}})
        inputs = {"amount": 5}
        new_comps, diff, msg = increment_handler(inputs, snapshot)
        
        assert new_comps[COUNTER_ID]["value"] == 15

    def test_reset_handler(self):
        snapshot = StateSnapshot(snapshot_id="1", components={COUNTER_ID: {"value": 99}})
        inputs = {}
        new_comps, diff, msg = reset_handler(inputs, snapshot)
        
        assert new_comps[COUNTER_ID]["value"] == 0
        assert diff[0].value == 0
