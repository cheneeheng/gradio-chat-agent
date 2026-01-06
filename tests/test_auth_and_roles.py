from gradio_chat_agent.persistence.db import make_engine, make_session_factory
from gradio_chat_agent.persistence.repo import StateRepository
from gradio_chat_agent.persistence.auth_repo import AuthRepository


def test_auth_verify_and_roles(tmp_path):
    db_url = f"sqlite:///{tmp_path}/t.sqlite3"
    engine = make_engine(db_url)
    sf = make_session_factory(engine)

    repo = StateRepository(sf)
    repo.create_tables(engine)

    auth = AuthRepository(sf)
    auth.ensure_default_admin(username="admin", password="admin")

    assert auth.verify_login("admin", "admin") is True
    ident = auth.get_identity("admin")
    assert "admin" in ident.roles
