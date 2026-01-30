import os
import pytest
from alembic.config import Config
from alembic import command
from sqlalchemy import create_engine, inspect
from gradio_chat_agent.persistence.sql_repository import SQLStateRepository

class TestAlembicSetup:
    def test_alembic_initial_migration(self, tmp_path):
        db_file = tmp_path / "test_alembic.db"
        db_url = f"sqlite:///{db_file}"
        
        # 1. Setup Alembic config
        alembic_cfg = Config("alembic.ini")
        alembic_cfg.set_main_option("sqlalchemy.url", db_url)
        
        # 2. Run migration
        command.upgrade(alembic_cfg, "head")
        
        # 3. Verify tables exist using SQLAlchemy inspector
        engine = create_engine(db_url)
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        
        expected_tables = [
            "projects", "users", "snapshots", "executions", 
            "session_facts", "locks", "api_tokens", "schedules",
            "project_limits", "project_memberships", "webhooks"
        ]
        
        for table in expected_tables:
            assert table in tables, f"Table {table} missing after migration"

    def test_sql_repository_auto_create_disabled(self, tmp_path):
        db_file = tmp_path / "test_no_auto.db"
        db_url = f"sqlite:///{db_file}"
        
        # Initialize repo with auto_create_tables=False
        repo = SQLStateRepository(db_url, auto_create_tables=False)
        
        # Verify no tables created
        engine = create_engine(db_url)
        inspector = inspect(engine)
        assert len(inspector.get_table_names()) == 0
        
    def test_sql_repository_auto_create_enabled_default(self, tmp_path):
        db_file = tmp_path / "test_auto_default.db"
        db_url = f"sqlite:///{db_file}"
        
        # Initialize repo (default should be True)
        repo = SQLStateRepository(db_url)
        
        # Verify tables created
        engine = create_engine(db_url)
        inspector = inspect(engine)
        assert "projects" in inspector.get_table_names()
