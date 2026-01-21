from unittest.mock import MagicMock
from gradio_chat_agent.models.enums import StateDiffOp
from gradio_chat_agent.models.execution_result import StateDiffEntry
from gradio_chat_agent.utils import compute_state_diff, encode_media, apply_state_diff


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

    def test_encode_media(self, tmp_path):
        p = tmp_path / "hello.txt"
        p.write_text("hello world")
        res = encode_media(str(p))
        assert "data" in res
        assert res["mime_type"] == "text/plain"

        p2 = tmp_path / "no_ext"
        p2.write_bytes(b"\x00\x01")
        res2 = encode_media(str(p2))
        assert res2["mime_type"] == "application/octet-stream"

    def test_apply_state_diff_coverage(self):
        # 1. Top-level add (lines 153-154)
        state = {}
        diffs = [StateDiffEntry(path="new_comp", op=StateDiffOp.ADD, value={"v": 1})]
        new_state = apply_state_diff(state, diffs)
        assert new_state["new_comp"] == {"v": 1}

        # 2. Path navigation creates dict (line 174)
        state = {"comp": {"a": 1}}
        diffs = [StateDiffEntry(path="comp.b.c", op=StateDiffOp.ADD, value=2)]
        new_state = apply_state_diff(state, diffs)
        assert new_state["comp"]["b"]["c"] == 2

        # 3. Path IS component ID (lines 179-182)
        state = {"comp": {"v": 1}}
        # Replace
        diffs = [StateDiffEntry(path="comp", op=StateDiffOp.REPLACE, value={"v": 2})]
        new_state = apply_state_diff(state, diffs)
        assert new_state["comp"] == {"v": 2}
        # Remove
        diffs = [StateDiffEntry(path="comp", op=StateDiffOp.REMOVE)]
        new_state = apply_state_diff(state, diffs)
        assert "comp" not in new_state

        # 4. Naive removal fallback (lines 199-208)
        state = {}
        diffs = [StateDiffEntry(path="a", op=StateDiffOp.REMOVE)]
        new_state = apply_state_diff(state, diffs)
        assert new_state == {}

        # 5. Force reach lines 204-206 using a mock
        mock_state = MagicMock()
        mock_state.__contains__.side_effect = [False, False, True]
        mock_state.get.return_value = {}
        mock_state.__getitem__.return_value = {}
        diffs = [StateDiffEntry(path="a.b", op=StateDiffOp.REMOVE)]
        apply_state_diff(mock_state, diffs)
        assert mock_state.__contains__.call_count >= 3

        # 6. Hit the break at line 205
        mock_state2 = MagicMock()
        mock_state2.__contains__.side_effect = [False, False, False, True]
        mock_state2.__getitem__.return_value = 1 # Not a dict
        diffs = [StateDiffEntry(path="a.b.c", op=StateDiffOp.REMOVE)]
        apply_state_diff(mock_state2, diffs)
        assert mock_state2.__contains__.call_count >= 4