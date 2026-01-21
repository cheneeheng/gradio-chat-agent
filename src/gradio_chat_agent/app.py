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
from gradio_chat_agent.registry.std_lib import (
    slider_component,
    slider_set_action,
    slider_set_handler,
    status_indicator_component,
    status_indicator_update_action,
    status_indicator_update_handler,
    text_input_component,
    text_input_set_action,
    text_input_set_handler,
)
from gradio_chat_agent.registry.system_actions import (
    forget_action,
    forget_handler,
    memory_component,
    remember_action,
    remember_handler,
)
from gradio_chat_agent.registry.web_automation import (
    browser_component,
    click_action,
    click_handler,
    navigate_action,
    navigate_handler,
    scroll_action,
    scroll_handler,
    sync_browser_state_action,
    sync_browser_state_handler,
    type_action,
    type_handler,
)
from gradio_chat_agent.ui.layout import create_ui
from gradio_chat_agent.utils import hash_password


logger = get_logger(__name__)


def bootstrap_admin(repository: SQLStateRepository):
    """Creates a default admin user if ALLOW_DEFAULT_ADMIN is enabled."""
    allow_default = (
        os.environ.get("ALLOW_DEFAULT_ADMIN", "True").lower() == "true"
    )
    if not allow_default:
        return

    admin_user = repository.get_user("admin")
    if not admin_user:
        logger.info("Bootstrapping default admin user...")
        repository.create_user("admin", hash_password("admin"))
        # Also add to default project as admin
        repository.add_project_member("default_project", "admin", "admin")


def create_registry() -> InMemoryRegistry:
    """Creates and populates the component and action registry."""
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

    # Standard Library Actions
    registry.register_component(text_input_component)
    registry.register_action(text_input_set_action, text_input_set_handler)
    registry.register_component(slider_component)
    registry.register_action(slider_set_action, slider_set_handler)
    registry.register_component(status_indicator_component)
    registry.register_action(
        status_indicator_update_action, status_indicator_update_handler
    )

    # Web Automation Actions
    registry.register_component(browser_component)
    registry.register_action(navigate_action, navigate_handler)
    registry.register_action(click_action, click_handler)
    registry.register_action(type_action, type_handler)
    registry.register_action(scroll_action, scroll_handler)
    registry.register_action(
        sync_browser_state_action, sync_browser_state_handler
    )
    return registry


def create_app() -> FastAPI:
    """Factory function to create and configure the FastAPI application.

    This is used by production ASGI servers like Gunicorn/Uvicorn with
    multiple worker processes.
    """
    setup_logging()

    # 1. Setup Registry
    registry = create_registry()

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

    # 3.5 Setup Alerting
    from gradio_chat_agent.observability.alerting import AlertingService

    alerting_service = AlertingService(engine)
    engine.add_post_execution_hook(alerting_service.check_execution_alerts)

    # 4. Setup Agent
    adapter = OpenAIAgentAdapter()

    # 5. Create FastAPI App
    app = FastAPI()

    # 6. Setup Auth
    from gradio_chat_agent.auth.manager import AuthManager
    from starlette.requests import Request
    from starlette.responses import RedirectResponse
    
    auth_manager = AuthManager(app)

    @app.get("/login")
    async def login(request: Request):
        redirect_uri = str(request.url_for("auth_callback"))
        return await auth_manager.login(request, redirect_uri)

    @app.get("/auth", name="auth_callback")
    async def auth_callback(request: Request):
        user = await auth_manager.auth_callback(request)
        if user:
            return RedirectResponse(url="/")
        return {"error": "Authentication failed"}

    @app.get("/logout")
    async def logout(request: Request):
        auth_manager.logout(request)
        return RedirectResponse(url="/")

    @app.get("/me")
    async def me(request: Request):
        user = auth_manager.get_current_user(request)
        return {"user": user}

    # 7. Build UI
    demo = create_ui(engine, adapter, auth_manager=auth_manager)

    # --- CORS Configuration ---
    allowed_origins = os.environ.get("GRADIO_ALLOWED_ORIGINS", "*").split(",")
    from fastapi.middleware.cors import CORSMiddleware

    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

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

    # Attach scheduler to app state for lifecycle management
    use_huey = os.environ.get("USE_HUEY", "False").lower() == "true"
    scheduler = SchedulerWorker(engine, use_huey=use_huey)
    app.state.scheduler = scheduler

    # Setup Browser Automation Observer
    from gradio_chat_agent.execution.browser_executor import BrowserExecutor
    from gradio_chat_agent.execution.observer import AuditLogObserver

    browser_executor = BrowserExecutor(engine)
    browser_observer = AuditLogObserver(engine, poll_interval=2.0)
    browser_observer.add_callback(browser_executor)
    app.state.browser_observer = browser_observer
    app.state.browser_executor = browser_executor

    @app.on_event("startup")
    def startup_event():
        app.state.scheduler.start()
        app.state.browser_observer.start()

    @app.on_event("shutdown")
    def shutdown_event():
        app.state.scheduler.stop()
        app.state.browser_observer.stop()
        app.state.browser_executor.stop()

    return gr.mount_gradio_app(app, demo, path="/")



def main():
    """Initializes and launches the Gradio Chat Agent application locally."""
    app = create_app()

    # 7. Launch
    server_name = os.environ.get("GRADIO_SERVER_NAME", "0.0.0.0")
    server_port = int(os.environ.get("GRADIO_SERVER_PORT", "7860"))

    logger.info(
        f"Starting Gradio Chat Agent with FastAPI on {server_name}:{server_port}..."
    )

    uvicorn.run(app, host=server_name, port=server_port)


if __name__ == "__main__":
    main()
