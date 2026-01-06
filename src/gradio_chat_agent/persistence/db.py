from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


DEFAULT_SQLITE_URL = "sqlite:///./gradio_chat_agent.sqlite3"


def make_engine(db_url: str = DEFAULT_SQLITE_URL):
    if db_url.startswith("sqlite:"):
        return create_engine(
            db_url, future=True, connect_args={"check_same_thread": False}
        )
    return create_engine(db_url, future=True)


def make_session_factory(engine):
    return sessionmaker(
        bind=engine, autoflush=False, autocommit=False, future=True
    )
