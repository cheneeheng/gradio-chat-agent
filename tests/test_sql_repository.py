from unittest.mock import MagicMock, patch
from datetime import datetime, timedelta, timezone
import pytest
from gradio_chat_agent.persistence.sql_repository import SQLStateRepository
from gradio_chat_agent.models.state_snapshot import StateSnapshot
from gradio_chat_agent.models.execution_result import ExecutionResult, ExecutionStatus, StateDiffEntry, ExecutionError
from gradio_chat_agent.models.enums import StateDiffOp

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

    def test_project_limits_partial(self, repo):
        pid = "p1"
        # Test partial sync (only rate)
        policy = {"limits": {"rate": {"per_minute": 5}}}
        repo.set_project_limits(pid, policy)
        with repo.SessionLocal() as session:
            from gradio_chat_agent.persistence.models import ProjectLimits
            row = session.get(ProjectLimits, pid)
            assert row.rate_limit_minute == 5
            assert row.rate_limit_hour == 1000 # default
            
        # Test partial sync (only budget)
        policy2 = {"limits": {"budget": {"daily": 200}}}
        repo.set_project_limits(pid, policy2)
        with repo.SessionLocal() as session:
            row = session.get(ProjectLimits, pid)
            assert row.daily_budget == 200

    def test_get_project_limits_raw_policy_none(self, repo):
        pid = "p_none"
        repo._ensure_project(pid)
        from gradio_chat_agent.persistence.models import ProjectLimits
        with repo.SessionLocal() as session:
            session.add(ProjectLimits(project_id=pid, raw_policy=None))
            session.commit()
        assert repo.get_project_limits(pid) == {}

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

    def test_sql_repository_full_flow(self, repo):
        pid = "p1"
        repo.create_project(pid, "P1")
        
        # Limits & Budgets
        repo.set_project_limits(pid, {"limits": {"rate": {"per_hour": 50}, "budget": {"daily": 100}}})
        assert repo.get_project_limits(pid)["limits"]["budget"]["daily"] == 100
        
        # Members
        repo.add_project_member(pid, "u1", "admin")
        repo.update_project_member_role(pid, "u1", "operator")
        members = repo.get_project_members(pid)
        assert members[0]["user_id"] == "u1"
        repo.remove_project_member(pid, "u1")
        assert len(repo.get_project_members(pid)) == 0
        
        # Facts
        repo.save_session_fact(pid, "u1", "k", "v")
        assert repo.get_session_facts(pid, "u1")["k"] == "v"
        
        # Snapshot
        repo.save_snapshot(pid, StateSnapshot(snapshot_id="s1", components={"c": {"v": 1}}))
        assert repo.get_snapshot("s1").components["c"]["v"] == 1
        assert repo.get_latest_snapshot(pid).snapshot_id == "s1"

        # Execution
        res = ExecutionResult(request_id="r1", action_id="a", status=ExecutionStatus.SUCCESS, state_snapshot_id="s1", metadata={"cost": 10})
        repo.save_execution(pid, res)
        assert repo.get_daily_budget_usage(pid) == 10.0

    def test_sql_repository_get_daily_budget_usage_no_metadata(self, repo):
        pid = "p1"
        repo.create_project(pid, "P1")
        from gradio_chat_agent.persistence.models import Execution, Snapshot
        with repo.SessionLocal() as session:
            session.add(Snapshot(id="s1", project_id=pid, components={}))
            session.add(Execution(
                request_id="r1", project_id=pid, action_id="a", status="success",
                state_snapshot_id="s1", state_diff=[], metadata_=None
            ))
            session.commit()
        
        usage = repo.get_daily_budget_usage(pid)
        assert usage == 0.0

    def test_sql_repository_is_project_archived_missing(self, repo):
        assert repo.is_project_archived("missing") is False

    def test_sql_repository_is_project_archived_true(self, repo):
        pid = "p1"
        repo.create_project(pid, "P1")
        repo.archive_project(pid)
        assert repo.is_project_archived(pid) is True

    def test_sql_repository_purge_project(self, repo):
        pid = "p1"
        repo.create_project(pid, "P1")
        repo.purge_project(pid)
        # Verify it's gone
        with repo.SessionLocal() as session:
            from gradio_chat_agent.persistence.models import Project
            assert session.get(Project, pid) is None

    def test_sql_repository_list_projects(self, repo):
        repo.create_project("p1", "Project 1")
        repo.create_project("p2", "Project 2")
        repo.archive_project("p2")
        
        projects = repo.list_projects()
        assert len(projects) >= 2
        p_ids = [p["id"] for p in projects]
        assert "p1" in p_ids
        assert "p2" in p_ids
        
        p2_data = [p for p in projects if p["id"] == "p2"][0]
        assert p2_data["archived"] is True

    def test_sql_repository_user_management(self, repo):
        repo.create_user("alice", "hash1")
        with repo.SessionLocal() as session:
            from gradio_chat_agent.persistence.models import User
            user = session.get(User, "alice")
            assert user.password_hash == "hash1"
            
        repo.update_user_password("alice", "hash2")
        with repo.SessionLocal() as session:
            user = session.get(User, "alice")
            assert user.password_hash == "hash2"

    def test_sql_repository_list_webhooks(self, repo):
        repo.save_webhook({"id": "wh1", "project_id": "p1", "action_id": "a", "secret": "s"})
        repo.save_webhook({"id": "wh2", "project_id": "p2", "action_id": "a", "secret": "s"})
        
        all_wh = repo.list_webhooks()
        assert len(all_wh) >= 2
        
        p1_wh = repo.list_webhooks(project_id="p1")
        assert len(p1_wh) == 1
        assert p1_wh[0]["id"] == "wh1"

    def test_check_health_failure(self, repo):
        # Mock SessionLocal to raise exception on context enter or execute
        with patch.object(repo, "SessionLocal") as mock_session_cls:
            mock_session = mock_session_cls.return_value
            mock_session.__enter__.return_value.execute.side_effect = Exception("DB Down")
            
            assert repo.check_health() is False
