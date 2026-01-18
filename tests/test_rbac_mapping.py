import pytest
from gradio_chat_agent.execution.engine import ExecutionEngine
from gradio_chat_agent.persistence.in_memory import InMemoryStateRepository
from gradio_chat_agent.registry.in_memory import InMemoryRegistry

class TestRBACMapping:
    @pytest.fixture
    def setup(self):
        registry = InMemoryRegistry()
        repository = InMemoryStateRepository()
        engine = ExecutionEngine(registry, repository)
        project_id = "test-p"
        repository.create_project(project_id, "Test")
        return engine, repository, project_id

    def test_resolve_user_roles_default(self, setup):
        engine, _, pid = setup
        # No user
        assert engine.resolve_user_roles(pid, None) == ["viewer"]
        # Non-existent user
        assert engine.resolve_user_roles(pid, "missing") == ["viewer"]

    def test_resolve_user_roles_explicit_membership(self, setup):
        engine, repo, pid = setup
        repo.create_user("u1", "h")
        repo.add_project_member(pid, "u1", "admin")
        
        assert engine.resolve_user_roles(pid, "u1") == ["admin"]

    def test_resolve_user_roles_dynamic_mapping(self, setup):
        engine, repo, pid = setup
        repo.set_project_limits(pid, {
            "role_mappings": [
                {"role": "operator", "condition": "user.email == 'staff@corp.com'"},
                {"role": "admin", "condition": "user.organization_id == 'admin_org'"}
            ]
        })
        
        # Match email
        repo.create_user("u1", "h", email="staff@corp.com")
        assert engine.resolve_user_roles(pid, "u1") == ["operator"]
        
        # Match org
        repo.create_user("u2", "h", organization_id="admin_org")
        assert engine.resolve_user_roles(pid, "u2") == ["admin"]
        
        # No match
        repo.create_user("u3", "h", email="guest@gmail.com")
        assert engine.resolve_user_roles(pid, "u3") == ["viewer"]

    def test_resolve_user_roles_explicit_overrides_dynamic(self, setup):
        engine, repo, pid = setup
        repo.set_project_limits(pid, {
            "role_mappings": [{"role": "admin", "condition": "True"}] # Everyone matches
        })
        
        repo.create_user("u1", "h")
        repo.add_project_member(pid, "u1", "viewer") # Explicitly viewer
        
        assert engine.resolve_user_roles(pid, "u1") == ["viewer"]

    def test_resolve_user_roles_safe_eval_error(self, setup):
        engine, repo, pid = setup
        repo.set_project_limits(pid, {
            "role_mappings": [{"role": "admin", "condition": "1/0"}] # Causes error
        })
        repo.create_user("u1", "h")
        
        # Should fallback to viewer and not crash
        assert engine.resolve_user_roles(pid, "u1") == ["viewer"]

    def test_resolve_user_roles_missing_condition_or_role(self, setup):
        engine, repo, pid = setup
        repo.set_project_limits(pid, {
            "role_mappings": [
                {"role": "admin"}, # Missing condition
                {"condition": "True"} # Missing role
            ]
        })
        repo.create_user("u1", "h")
        assert engine.resolve_user_roles(pid, "u1") == ["viewer"]
