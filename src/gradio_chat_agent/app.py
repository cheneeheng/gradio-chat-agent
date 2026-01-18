"""Main entry point for the Gradio Chat Agent application.

This module initializes the core components of the system, including the
registries, persistence layer, execution engine, and chat agent, then launches
the Gradio web interface.
"""

import os
import sys

import gradio as gr
import uvicorn
from fastapi import FastAPI, Response

# Ensure src is in path
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from gradio_chat_agent.chat.openai_adapter import OpenAIAgentAdapter
from gradio_chat_agent.execution.engine import ExecutionEngine
from gradio_chat_agent.execution.scheduler import SchedulerWorker
from gradio_chat_agent.observability.logging import get_logger, setup_logging
from gradio_chat_agent.observability.metrics import (
    CONTENT_TYPE_LATEST,
    get_metrics_content,
)
from gradio_chat_agent.persistence.sql_repository import SQLStateRepository
from gradio_chat_agent.registry.demo_actions import (
    counter_component,
    increment_action,
    increment_handler,
    reset_action,
    reset_handler,
    set_action,
    set_handler,
)
from gradio_chat_agent.registry.in_memory import InMemoryRegistry

# Import components/actions
from gradio_chat_agent.registry.system_actions import (
    forget_action,
    forget_handler,
    memory_component,
    remember_action,
    remember_handler,
)
from gradio_chat_agent.ui.layout import create_ui
from gradio_chat_agent.utils import hash_password

logger = get_logger(__name__)


def bootstrap_admin(repository: SQLStateRepository):
    """Creates a default admin user if ALLOW_DEFAULT_ADMIN is enabled."""
    allow_default = os.environ.get("ALLOW_DEFAULT_ADMIN", "True").lower() == "true"
    if not allow_default:
        return

    admin_user = repository.get_user("admin")
    if not admin_user:
        logger.info("Bootstrapping default admin user...")
        repository.create_user("admin", hash_password("admin"))
        # Also add to default project as admin
        repository.add_project_member("default_project", "admin", "admin")


def main():
    """Initializes and launches the Gradio Chat Agent application.

    This function sets up the following:
    1. The Action and Component registries with system and demo actions.
    2. The SQL persistence layer (SQLite by default).
    3. The authoritative Execution Engine.
    4. The OpenAI-based Chat Agent adapter.
    5. The Gradio UI layout.

    It then launches the server on port 7860.
    """
    setup_logging()

    # 1. Setup Registry
    registry = InMemoryRegistry()

    # System Actions
    registry.register_component(memory_component)
    registry.register_action(remember_action, remember_handler)
    registry.register_action(forget_action, forget_handler)

    # Demo Actions
    registry.register_component(counter_component)
    registry.register_action(set_action, set_handler)
    registry.register_action(increment_action, increment_handler)
    registry.register_action(reset_action, reset_handler)

    # 2. Setup Persistence
    db_url = os.environ.get(
        "DATABASE_URL", "sqlite:///gradio_chat_agent.sqlite3"
    )
    logger.info(f"Connecting to database: {db_url}")
    repository = SQLStateRepository(db_url)

    # 2.5 Bootstrap Admin
    bootstrap_admin(repository)

    # 3. Setup Engine
    engine = ExecutionEngine(registry=registry, repository=repository)

    # 3.5 Start Scheduler
    scheduler = SchedulerWorker(engine)
    scheduler.start()

    # 4. Setup Agent
    # Note: Requires OPENAI_API_KEY env var
    adapter = OpenAIAgentAdapter()

    # 5. Build UI
    demo = create_ui(engine, adapter)

    # 6. Create FastAPI App and mount everything
    app = FastAPI()

    @app.get("/metrics")
    def metrics():
        return Response(
            content=get_metrics_content(), media_type=CONTENT_TYPE_LATEST
        )

    @app.get("/health")
    def health():
        db_healthy = repository.check_health()
        status = "healthy" if db_healthy else "unhealthy"
        code = 200 if db_healthy else 503
        return Response(
            content=f'{{"status": "{status}", "database": {"true" if db_healthy else "false"}}}',
            status_code=code,
            media_type="application/json",
        )

    app = gr.mount_gradio_app(app, demo, path="/")

    # 7. Launch
    server_name = os.environ.get("GRADIO_SERVER_NAME", "0.0.0.0")
    server_port = int(os.environ.get("GRADIO_SERVER_PORT", "7860"))

    logger.info(f"Starting Gradio Chat Agent with FastAPI on {server_name}:{server_port}...")

    try:
        uvicorn.run(app, host=server_name, port=server_port)
    finally:
        scheduler.stop()


if __name__ == "__main__":
    main()
