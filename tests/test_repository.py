from datetime import datetime, timedelta, timezone
import pytest
from gradio_chat_agent.persistence.in_memory import InMemoryStateRepository
from gradio_chat_agent.persistence.sql_repository import SQLStateRepository
from gradio_chat_agent.models.state_snapshot import StateSnapshot
from gradio_chat_agent.models.execution_result import ExecutionResult, ExecutionStatus, StateDiffEntry, ExecutionError
from gradio_chat_agent.models.enums import StateDiffOp

class TestInMemoryRepository:
    def test_session_facts(self):
        repo = InMemoryStateRepository()
        pid = "proj1"
        uid = "user1"
        
        # Empty initially
        assert repo.get_session_facts(pid, uid) == {}
        
        # Save fact
        repo.save_session_fact(pid, uid, "theme", "dark")
        facts = repo.get_session_facts(pid, uid)
        assert facts["theme"] == "dark"
        
        # Update fact
        repo.save_session_fact(pid, uid, "theme", "light")
        assert repo.get_session_facts(pid, uid)["theme"] == "light"
        
        # Delete fact
        repo.delete_session_fact(pid, uid, "theme")
        assert "theme" not in repo.get_session_facts(pid, uid)

    def test_session_facts_isolation(self):
        repo = InMemoryStateRepository()
        
        # Save for User 1
        repo.save_session_fact("p1", "u1", "key", "val1")
        
        # Check User 2 (same project)
        assert "key" not in repo.get_session_facts("p1", "u2")
        
        # Check User 1 (diff project)
        assert "key" not in repo.get_session_facts("p2", "u1")

    def test_repo_edges(self):
        repo = InMemoryStateRepository()
        pid = "proj-edge"
        
        # Get latest snapshot empty
        assert repo.get_latest_snapshot("empty_proj") is None
        
        # Get webhook missing
        assert repo.get_webhook("missing") is None
        
        # Get schedule explicit
        repo._schedules["s1"] = {"id": "s1"}
        assert repo.get_schedule("s1") is not None
        
        # Purge cleanup
        repo.create_project(pid, "Cleanup")
        repo.add_project_member(pid, "u", "viewer")
        repo.save_session_fact(pid, "u", "k", "v")
        repo._webhooks["w1"] = {"id": "w1", "project_id": pid}
        repo._schedules["s1"] = {"id": "s1", "project_id": pid}
        
        repo.purge_project(pid)
        
        assert repo.get_project_members(pid) == []
        assert repo.get_session_facts(pid, "u") == {}
        assert "w1" not in repo._webhooks
        assert "s1" not in repo._schedules

    def test_get_snapshot_found(self):
        repo = InMemoryStateRepository()
        snap = StateSnapshot(snapshot_id="s1", components={})
        repo.save_snapshot("p1", snap)
        assert repo.get_snapshot("s1") == snap

    def test_delete_webhook_missing(self):
        repo = InMemoryStateRepository()
        # Should not raise
        repo.delete_webhook("missing")

    def test_delete_schedule_missing(self):
        repo = InMemoryStateRepository()
        # Should not raise
        repo.delete_schedule("missing")

    def test_archive_project(self):
        repo = InMemoryStateRepository()
        repo.create_project("p1", "Project 1")
        assert repo._projects["p1"]["archived_at"] is None
        repo.archive_project("p1")
        assert repo._projects["p1"]["archived_at"] is not None
        
        # archive missing
        repo.archive_project("missing") # should not crash

    def test_project_members(self):
        repo = InMemoryStateRepository()
        repo.create_project("p1", "P1")
        repo.add_project_member("p1", "u1", "viewer")
        repo.update_project_member_role("p1", "u1", "admin")
        
        members = repo.get_project_members("p1")
        assert len(members) == 1
        assert members[0]["user_id"] == "u1"
        assert members[0]["role"] == "admin"

class TestSQLRepository:
    @pytest.fixture
    def repo(self):
        # Use in-memory SQLite for testing
        return SQLStateRepository("sqlite:///:memory:")

    def test_ensure_project(self, repo):
        repo._ensure_project("new-proj")
        # Should not error if called again
        repo._ensure_project("new-proj")

    def test_snapshots(self, repo):
        pid = "p1"
        snap = StateSnapshot(snapshot_id="s1", components={"c": {"v": 1}})
        repo.save_snapshot(pid, snap)
        
        # Get latest
        latest = repo.get_latest_snapshot(pid)
        assert latest.snapshot_id == "s1"
        assert latest.components == {"c": {"v": 1}}
        
        # Get by ID
        found = repo.get_snapshot("s1")
        assert found.snapshot_id == "s1"
        
        # Missing
        assert repo.get_snapshot("missing") is None
        assert repo.get_latest_snapshot("missing") is None

    def test_executions(self, repo):
        pid = "p1"
        res = ExecutionResult(
            request_id="r1", action_id="a1", status=ExecutionStatus.SUCCESS,
            state_snapshot_id="s1", state_diff=[StateDiffEntry(path="c.v", op=StateDiffOp.REPLACE, value=2)],
            error=None
        )
        repo.save_execution(pid, res)
        
        history = repo.get_execution_history(pid)
        assert len(history) == 1
        assert history[0].request_id == "r1"
        assert history[0].state_diff[0].path == "c.v"

        # Failed execution with error
        res_fail = ExecutionResult(
            request_id="r2", action_id="a1", status=ExecutionStatus.FAILED,
            state_snapshot_id="s1", error=ExecutionError(code="err", detail="fail")
        )
        repo.save_execution(pid, res_fail)
        history = repo.get_execution_history(pid)
        assert len(history) == 2
        assert history[0].error.code == "err"

    def test_session_facts(self, repo):
        pid = "p1"
        uid = "u1"
        repo.save_session_fact(pid, uid, "k", "v")
        assert repo.get_session_facts(pid, uid) == {"k": "v"}
        
        repo.save_session_fact(pid, uid, "k", "v2") # Update
        assert repo.get_session_facts(pid, uid) == {"k": "v2"}
        
        repo.delete_session_fact(pid, uid, "k")
        assert repo.get_session_facts(pid, uid) == {}

    def test_project_limits(self, repo):
        pid = "p1"
        policy = {"limits": {"rate": {"per_minute": 10, "per_hour": 100}, "budget": {"daily": 1000}}}
        repo.set_project_limits(pid, policy)
        
        fetched = repo.get_project_limits(pid)
        assert fetched == policy
        assert repo.get_project_limits("missing") == {}

    def test_count_recent_executions(self, repo):
        pid = "p1"
        res = ExecutionResult(
            request_id="r1", action_id="a1", status=ExecutionStatus.SUCCESS,
            state_snapshot_id="s1", timestamp=datetime.now(timezone.utc)
        )
        repo.save_execution(pid, res)
        
        # In last minute: 1
        assert repo.count_recent_executions(pid, 1) == 1
        
        # Mock older execution
        res2 = ExecutionResult(
            request_id="r2", action_id="a1", status=ExecutionStatus.SUCCESS,
            state_snapshot_id="s1", timestamp=datetime.now(timezone.utc) - timedelta(minutes=10)
        )
        repo.save_execution(pid, res2)
        
        # In last 5 minutes: still 1
        assert repo.count_recent_executions(pid, 5) == 1
        # In last 15 minutes: 2
        assert repo.count_recent_executions(pid, 15) == 2
        
    def test_webhooks(self, repo):
        pid = "p1"
        config = {"id": "wh1", "project_id": pid, "action_id": "a1", "secret": "s", "enabled": True}
        repo.save_webhook(config)
        
        fetched = repo.get_webhook("wh1")
        assert fetched["action_id"] == "a1"
        
        # Update
        config["action_id"] = "a2"
        repo.save_webhook(config)
        assert repo.get_webhook("wh1")["action_id"] == "a2"
        
        assert repo.get_webhook("missing") is None
        
        repo.delete_webhook("wh1")
        assert repo.get_webhook("wh1") is None

    def test_schedules(self, repo):
        pid = "p1"
        config = {"id": "sch1", "project_id": pid, "action_id": "a1", "cron": "* * * * *", "enabled": True}
        repo.save_schedule(config)
        
        fetched = repo.get_schedule("sch1")
        assert fetched["action_id"] == "a1"
        
        # Update
        config["action_id"] = "a2"
        repo.save_schedule(config)
        assert repo.get_schedule("sch1")["action_id"] == "a2"
        
        assert repo.get_schedule("missing") is None
        
        repo.delete_schedule("sch1")
        assert repo.get_schedule("sch1") is None

    def test_project_lifecycle(self, repo):
        repo.create_project("p2", "Project 2")
        repo.archive_project("p2")
        repo.purge_project("p2")

    def test_membership(self, repo):
        pid = "p1"
        repo.add_project_member(pid, "u1", "viewer")
        members = repo.get_project_members(pid)
        assert len(members) == 1
        assert members[0]["role"] == "viewer"
        
        repo.update_project_member_role(pid, "u1", "admin")
        assert repo.get_project_members(pid)[0]["role"] == "admin"
        
        repo.remove_project_member(pid, "u1")
        assert len(repo.get_project_members(pid)) == 0
