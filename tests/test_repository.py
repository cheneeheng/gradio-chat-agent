from gradio_chat_agent.persistence.in_memory import InMemoryStateRepository
from gradio_chat_agent.models.state_snapshot import StateSnapshot

class TestRepository:
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
