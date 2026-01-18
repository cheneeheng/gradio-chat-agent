"""Executor for web automation actions using Playwright."""

import uuid
from typing import Optional

from playwright.sync_api import sync_playwright

from gradio_chat_agent.models.enums import IntentType
from gradio_chat_agent.models.intent import ChatIntent
from gradio_chat_agent.observability.logging import get_logger

logger = get_logger(__name__)


class BrowserExecutor:
    """Executes queued browser actions using Playwright.

    This class is designed to be used as a callback for an AuditLogObserver.
    It watches for successful 'browser.*' actions that set a 'pending_action',
    executes them, and syncs the resulting browser state back to the engine.
    """

    def __init__(self, engine):
        """Initializes the browser executor.

        Args:
            engine: The authoritative execution engine.
        """
        self.engine = engine
        self._playwright = None
        self._browser = None
        self._pages = {}  # project_id -> page

    def _ensure_browser(self):
        """Ensures that the Playwright browser is launched."""
        if not self._playwright:
            self._playwright = sync_playwright().start()
            self._browser = self._playwright.chromium.launch(headless=True)

    def _get_page(self, project_id: str):
        """Retrieves or creates a browser page for a specific project."""
        if project_id not in self._pages:
            self._pages[project_id] = self._browser.new_page()
        return self._pages[project_id]

    def __call__(self, project_id: str, result):
        """Callback for the AuditLogObserver.

        Args:
            project_id: The ID of the project.
            result: The successful execution result.
        """
        # Only process browser actions (except the internal sync.state)
        if not result.action_id.startswith("browser.") or result.action_id == "browser.sync.state":
            return

        logger.info(f"Processing browser action: {result.action_id} for project {project_id}")

        # 1. Fetch current state to get the pending action
        snapshot = self.engine.repository.get_latest_snapshot(project_id)
        if not snapshot:
            return

        browser_state = snapshot.components.get("browser")
        if not browser_state or not browser_state.get("pending_action"):
            logger.debug(f"No pending action found for project {project_id}")
            return

        pending = browser_state["pending_action"]
        action_type = pending["type"]
        params = pending["params"]

        # 2. Execute using Playwright
        try:
            self._ensure_browser()
            page = self._get_page(project_id)

            res_msg = ""
            if action_type == "navigate":
                url = params["url"]
                page.goto(url)
                res_msg = f"Navigated to {url}"
            elif action_type == "click":
                selector = params["selector"]
                page.click(selector)
                res_msg = f"Clicked element: {selector}"
            elif action_type == "type":
                selector = params["selector"]
                text = params["text"]
                page.fill(selector, text)
                res_msg = f"Typed '{text}' into {selector}"
            elif action_type == "scroll":
                direction = params["direction"]
                amount = params.get("amount", 500)
                if direction == "down":
                    page.evaluate(f"window.scrollBy(0, {amount})")
                else:
                    page.evaluate(f"window.scrollBy(0, -{amount})")
                res_msg = f"Scrolled {direction} by {amount}px"
            else:
                logger.warning(f"Unknown browser action type: {action_type}")
                return

            # 3. Synchronize state back
            sync_intent = ChatIntent(
                type=IntentType.ACTION_CALL,
                request_id=f"sync-{uuid.uuid4().hex[:8]}",
                action_id="browser.sync.state",
                inputs={
                    "url": page.url,
                    "title": page.title(),
                    "status": "idle",
                    "last_action_result": res_msg,
                    "last_error": None
                }
            )
            self.engine.execute_intent(
                project_id=project_id,
                intent=sync_intent,
                user_roles=["admin"],
                user_id="system_browser"
            )
            logger.info(f"Browser action '{action_type}' completed and synced.")

        except Exception as e:
            logger.exception(f"Error executing browser action '{action_type}': {str(e)}")
            # Sync error state
            error_intent = ChatIntent(
                type=IntentType.ACTION_CALL,
                request_id=f"err-{uuid.uuid4().hex[:8]}",
                action_id="browser.sync.state",
                inputs={
                    "status": "error",
                    "last_error": str(e)
                }
            )
            self.engine.execute_intent(
                project_id=project_id,
                intent=error_intent,
                user_roles=["admin"],
                user_id="system_browser"
            )

    def stop(self):
        """Closes the browser and stops Playwright."""
        if self._playwright:
            if self._browser:
                self._browser.close()
            self._playwright.stop()
            self._playwright = None
            self._browser = None
            self._pages = {}
