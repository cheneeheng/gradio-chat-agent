import pytest
from datetime import datetime, timedelta
from gradio_chat_agent.persistence.in_memory import InMemoryStateRepository
from gradio_chat_agent.models.state_snapshot import StateSnapshot

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

    def test_in_memory_repository_edge_cases(self):
        repo = InMemoryStateRepository()
        repo.create_project("p1", "P1")
        snap = StateSnapshot(snapshot_id="s1", components={"c": {}})
        repo.save_snapshot("p1", snap)
        assert repo.get_snapshot("s1").snapshot_id == "s1"
        assert repo.get_snapshot("missing") is None
        
        # Facts deletion
        repo.save_session_fact("p1", "u1", "k", "v")
        repo.delete_session_fact("p1", "u1", "k")
        assert repo.get_session_facts("p1", "u1") == {}
        
        # Project archival check
        assert repo.is_project_archived("p1") is False
        repo.archive_project("p1")
        assert repo.is_project_archived("p1") is True

    def test_budget_and_recent_counts(self):
        repo = InMemoryStateRepository()
        pid = "p1"
        from gradio_chat_agent.models.execution_result import ExecutionResult, ExecutionStatus
        from datetime import datetime, timedelta, timezone
        
        now = datetime.now(timezone.utc)
        
        # Success with cost
        res1 = ExecutionResult(
            request_id="r1", action_id="a", status=ExecutionStatus.SUCCESS, 
            state_snapshot_id="s", metadata={"cost": 10},
            timestamp=now
        )
        repo.save_execution(pid, res1)
        
        # Failed (should be counted for rate limits, but ignored for budget)
        res2 = ExecutionResult(
            request_id="r2", action_id="a", status=ExecutionStatus.FAILED, 
            state_snapshot_id="s", metadata={"cost": 100},
            timestamp=now
        )
        repo.save_execution(pid, res2)
        
        # Old success (should be ignored by budget)
        res3 = ExecutionResult(
            request_id="r3", action_id="a", status=ExecutionStatus.SUCCESS, 
            state_snapshot_id="s", metadata={"cost": 1000},
            timestamp=now - timedelta(days=2)
        )
        repo.save_execution(pid, res3)
        
        assert repo.get_daily_budget_usage(pid) == 10.0
        # Should count BOTH success and failure in the last hour
        assert repo.count_recent_executions(pid, 60) == 2

    def test_schedule_management(self):
        repo = InMemoryStateRepository()
        sch = {"id": "s1", "project_id": "p1", "action_id": "a"}
        repo.save_schedule(sch)
        assert repo.get_schedule("s1") == sch
        repo.delete_schedule("s1")
        assert repo.get_schedule("s1") is None
        repo.delete_schedule("missing") # should not crash

    def test_get_user(self):
        repo = InMemoryStateRepository()
        assert repo.get_user("missing") is None
        repo.create_user("u1", "h")
        assert repo.get_user("u1")["id"] == "u1"

    def test_list_webhooks_filtered(self):
        repo = InMemoryStateRepository()
        repo.save_webhook({"id": "w1", "project_id": "p1"})
        repo.save_webhook({"id": "w2", "project_id": "p2"})
        
        filtered = repo.list_webhooks(project_id="p1")
        assert len(filtered) == 1
        assert filtered[0]["id"] == "w1"

    def test_update_user_password(self):
        repo = InMemoryStateRepository()
        repo.create_user("u1", "old")
        
        # Success
        repo.update_user_password("u1", "new")
        assert repo.get_user("u1")["password_hash"] == "new"
        
        # Non-existent (no error)
        repo.update_user_password("missing", "new")

    def test_get_latest_snapshot_empty_coverage(self):
        repo = InMemoryStateRepository()
        # Ensure project dict exists but is empty
        repo._snapshots["p1"] = []
        assert repo.get_latest_snapshot("p1") is None

    def test_delete_user_with_memberships(self):
        repo = InMemoryStateRepository()
        repo.create_user("u1", "h")
        repo.add_project_member("p1", "u1", "admin")
        assert len(repo.get_project_members("p1")) == 1
        
        repo.delete_user("u1")
        assert repo.get_user("u1") is None
        assert len(repo.get_project_members("p1")) == 0

    def test_list_webhooks_all(self):
        repo = InMemoryStateRepository()
        repo.save_webhook({"id": "w1", "project_id": "p1"})
        repo.save_webhook({"id": "w2", "project_id": "p2"})
        
        all_wh = repo.list_webhooks() # project_id=None
        assert len(all_wh) == 2

    def test_in_memory_lock_expired(self):
        repo = InMemoryStateRepository()
        pid = "p1"
        # Acquire a lock that expires immediately
        repo.acquire_lock(pid, "h1", timeout_seconds=-1)
        
        # Another holder should be able to take it
        assert repo.acquire_lock(pid, "h2", timeout_seconds=10) is True
        assert repo._locks[pid]["holder_id"] == "h2"