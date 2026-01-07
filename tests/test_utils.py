from gradio_chat_agent.models.enums import StateDiffOp
from gradio_chat_agent.utils import compute_state_diff


class TestUtils:
    def test_compute_state_diff_add(self):
        old = {}
        new = {"a": 1}
        diff = compute_state_diff(old, new)
        assert len(diff) == 1
        assert diff[0].path == "a"
        assert diff[0].op == StateDiffOp.ADD
        assert diff[0].value == 1

    def test_compute_state_diff_remove(self):
        old = {"a": 1}
        new = {}
        diff = compute_state_diff(old, new)
        assert len(diff) == 1
        assert diff[0].path == "a"
        assert diff[0].op == StateDiffOp.REMOVE
        assert diff[0].value is None

    def test_compute_state_diff_replace(self):
        old = {"a": 1}
        new = {"a": 2}
        diff = compute_state_diff(old, new)
        assert len(diff) == 1
        assert diff[0].path == "a"
        assert diff[0].op == StateDiffOp.REPLACE
        assert diff[0].value == 2

    def test_compute_state_diff_nested(self):
        old = {"a": {"b": 1}}
        new = {"a": {"b": 2, "c": 3}}
        diff = compute_state_diff(old, new)
        # 1 replace (b), 1 add (c)
        paths = [d.path for d in diff]
        assert "a.b" in paths
        assert "a.c" in paths
