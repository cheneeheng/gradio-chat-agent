from gradio_chat_agent.persistence.in_memory import InMemoryStateRepository

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
