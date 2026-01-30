"""Huey-based tasks for background execution."""

import os
from huey import SqliteHuey
from gradio_chat_agent.execution.engine import ExecutionEngine
from gradio_chat_agent.persistence.sql_repository import SQLStateRepository
from gradio_chat_agent.registry.in_memory import InMemoryRegistry
from gradio_chat_agent.models.intent import ChatIntent
from gradio_chat_agent.models.enums import IntentType, ExecutionMode
import uuid

# Initialize Huey with a SQLite database for the queue
db_path = os.environ.get("HUEY_DB_PATH", "huey_queue.db")
huey = SqliteHuey(filename=db_path)

# Global instances for the worker process
_engine = None

def get_engine():
    global _engine
    if _engine is None:
        # Re-initialize engine components for the worker process
        # In a real app, this would use a proper DI or config loader
        db_url = os.environ.get("DATABASE_URL", "sqlite:///gradio_chat_agent.sqlite3")
        repo = SQLStateRepository(db_url, auto_create_tables=False)
        
        # We need to re-register all actions/components if using InMemoryRegistry
        # or use a persistent registry if available.
        # For this implementation, we'll re-register basic ones or assume a common setup function.
        from gradio_chat_agent.app import create_registry
        registry = create_registry()
        _engine = ExecutionEngine(registry, repo)
    return _engine

@huey.task()
def execute_background_action(project_id: str, action_id: str, inputs: dict, user_id: str, trigger_type: str):
    """Executes an action in the background."""
    engine = get_engine()
    
    intent = ChatIntent(
        type=IntentType.ACTION_CALL,
        request_id=f"bg-{trigger_type}-{uuid.uuid4().hex[:8]}",
        action_id=action_id,
        inputs=inputs,
        execution_mode=ExecutionMode.AUTONOMOUS,
        confirmed=True,
        trace={"trigger": trigger_type}
    )
    
    # System users for automated triggers
    user_roles = ["admin"] 
    
    return engine.execute_intent(
        project_id=project_id,
        intent=intent,
        user_roles=user_roles,
        user_id=user_id
    )
