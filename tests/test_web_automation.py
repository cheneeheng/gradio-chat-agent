import pytest
import uuid
from unittest.mock import MagicMock, patch
from gradio_chat_agent.execution.engine import ExecutionEngine
from gradio_chat_agent.execution.browser_executor import BrowserExecutor
from gradio_chat_agent.persistence.in_memory import InMemoryStateRepository
from gradio_chat_agent.registry.in_memory import InMemoryRegistry
from gradio_chat_agent.registry.web_automation import (
    browser_component,
    navigate_action, navigate_handler,
    click_action, click_handler,
    type_action, type_handler,
    scroll_action, scroll_handler,
    sync_browser_state_action, sync_browser_state_handler,
    BROWSER_ID
)
from gradio_chat_agent.models.intent import ChatIntent
from gradio_chat_agent.models.enums import IntentType, ExecutionStatus, ExecutionMode
from gradio_chat_agent.models.state_snapshot import StateSnapshot

class TestWebAutomation:
    @pytest.fixture
    def setup(self):
        registry = InMemoryRegistry()
        repository = InMemoryStateRepository()
        engine = ExecutionEngine(registry, repository)
        project_id = "test-browser"
        
        registry.register_component(browser_component)
        registry.register_action(navigate_action, navigate_handler)
        registry.register_action(click_action, click_handler)
        registry.register_action(type_action, type_handler)
        registry.register_action(scroll_action, scroll_handler)
        registry.register_action(sync_browser_state_action, sync_browser_state_handler)
        
        return engine, registry, repository, project_id

    def test_navigate_handler(self, setup):
        engine, registry, repo, pid = setup
        intent = ChatIntent(
            type=IntentType.ACTION_CALL,
            request_id="r1",
            action_id="browser.navigate",
            inputs={"url": "https://example.com"}
        )
        res = engine.execute_intent(pid, intent, user_roles=["admin"])
        assert res.status == ExecutionStatus.SUCCESS
        
        latest = repo.get_latest_snapshot(pid)
        state = latest.components[BROWSER_ID]
        assert state["status"] == "busy"
        assert state["pending_action"]["type"] == "navigate"
        assert state["pending_action"]["params"]["url"] == "https://example.com"

    def test_sync_browser_state_handler(self, setup):
        engine, registry, repo, pid = setup
        intent = ChatIntent(
            type=IntentType.ACTION_CALL,
            request_id="r1",
            action_id="browser.sync.state",
            inputs={
                "url": "https://synced.com",
                "title": "Synced",
                "status": "idle"
            }
        )
        res = engine.execute_intent(pid, intent, user_roles=["admin"])
        assert res.status == ExecutionStatus.SUCCESS
        
        latest = repo.get_latest_snapshot(pid)
        state = latest.components[BROWSER_ID]
        assert state["url"] == "https://synced.com"
        assert state["title"] == "Synced"
        assert state["status"] == "idle"
        assert state["pending_action"] is None

    @patch("gradio_chat_agent.execution.browser_executor.sync_playwright")
    def test_browser_executor_success(self, mock_sync_pw, setup):
        engine, _, repo, pid = setup
        executor = BrowserExecutor(engine)
        
        # Mock Playwright
        mock_pw = mock_sync_pw.return_value.start.return_value
        mock_browser = mock_pw.chromium.launch.return_value
        mock_page = mock_browser.new_page.return_value
        mock_page.url = "https://example.com"
        mock_page.title.return_value = "Example Domain"
        
        # 1. Queue an action
        intent = ChatIntent(
            type=IntentType.ACTION_CALL,
            request_id="r1",
            action_id="browser.navigate",
            inputs={"url": "https://example.com"}
        )
        res = engine.execute_intent(pid, intent, user_roles=["admin"])
        
        # 2. Run executor
        executor(pid, res)
        
        # Verify Playwright calls
        mock_page.goto.assert_called_with("https://example.com")
        
        # Verify state synced back
        latest = repo.get_latest_snapshot(pid)
        assert latest.components[BROWSER_ID]["url"] == "https://example.com"
        assert latest.components[BROWSER_ID]["status"] == "idle"
        
        executor.stop()

    @patch("gradio_chat_agent.execution.browser_executor.sync_playwright")
    def test_browser_executor_click(self, mock_sync_pw, setup):
        engine, _, repo, pid = setup
        executor = BrowserExecutor(engine)
        
        # Mock
        mock_pw = mock_sync_pw.return_value.start.return_value
        mock_browser = mock_pw.chromium.launch.return_value
        mock_page = mock_browser.new_page.return_value
        
        intent = ChatIntent(
            type=IntentType.ACTION_CALL, request_id="r1",
            action_id="browser.click", inputs={"selector": "button"}
        )
        res = engine.execute_intent(pid, intent, user_roles=["admin"])
        executor(pid, res)
        
        mock_page.click.assert_called_with("button")
        executor.stop()

    @patch("gradio_chat_agent.execution.browser_executor.sync_playwright")
    def test_browser_executor_type(self, mock_sync_pw, setup):
        engine, _, repo, pid = setup
        executor = BrowserExecutor(engine)
        
        mock_pw = mock_sync_pw.return_value.start.return_value
        mock_browser = mock_pw.chromium.launch.return_value
        mock_page = mock_browser.new_page.return_value
        
        intent = ChatIntent(
            type=IntentType.ACTION_CALL, request_id="r1",
            action_id="browser.type", inputs={"selector": "input", "text": "hello"}
        )
        res = engine.execute_intent(pid, intent, user_roles=["admin"])
        executor(pid, res)
        
        mock_page.fill.assert_called_with("input", "hello")
        executor.stop()

    @patch("gradio_chat_agent.execution.browser_executor.sync_playwright")
    def test_browser_executor_scroll(self, mock_sync_pw, setup):
        engine, _, repo, pid = setup
        executor = BrowserExecutor(engine)
        
        mock_pw = mock_sync_pw.return_value.start.return_value
        mock_browser = mock_pw.chromium.launch.return_value
        mock_page = mock_browser.new_page.return_value
        
        # Down
        intent = ChatIntent(
            type=IntentType.ACTION_CALL, request_id="r1",
            action_id="browser.scroll", inputs={"direction": "down", "amount": 100}
        )
        res = engine.execute_intent(pid, intent, user_roles=["admin"])
        executor(pid, res)
        mock_page.evaluate.assert_called_with("window.scrollBy(0, 100)")
        
        # Up
        intent2 = ChatIntent(
            type=IntentType.ACTION_CALL, request_id="r2",
            action_id="browser.scroll", inputs={"direction": "up", "amount": 200}
        )
        res2 = engine.execute_intent(pid, intent2, user_roles=["admin"])
        executor(pid, res2)
        mock_page.evaluate.assert_called_with("window.scrollBy(0, -200)")
        
        executor.stop()

    @patch("gradio_chat_agent.execution.browser_executor.sync_playwright")
    def test_browser_executor_error(self, mock_sync_pw, setup):
        engine, _, repo, pid = setup
        executor = BrowserExecutor(engine)
        
        mock_pw = mock_sync_pw.return_value.start.return_value
        mock_browser = mock_pw.chromium.launch.return_value
        mock_page = mock_browser.new_page.return_value
        mock_page.goto.side_effect = Exception("Network Error")
        
        intent = ChatIntent(
            type=IntentType.ACTION_CALL, request_id="r1",
            action_id="browser.navigate", inputs={"url": "https://fail.com"}
        )
        res = engine.execute_intent(pid, intent, user_roles=["admin"])
        executor(pid, res)
        
        latest = repo.get_latest_snapshot(pid)
        assert latest.components[BROWSER_ID]["status"] == "error"
        assert "Network Error" in latest.components[BROWSER_ID]["last_error"]
        executor.stop()

    def test_browser_executor_ignored_actions(self, setup):
        engine, _, _, pid = setup
        executor = BrowserExecutor(engine)
        
        # Non-browser action
        res = MagicMock(action_id="other.action")
        executor(pid, res)
        # Should not throw and not call anything
        
        # Sync state action itself should be ignored
        res2 = MagicMock(action_id="browser.sync.state")
        executor(pid, res2)

    def test_browser_executor_no_snapshot(self, setup):
        engine, _, _, pid = setup
        executor = BrowserExecutor(engine)
        
        res = MagicMock(action_id="browser.navigate")
        with patch.object(engine.repository, "get_latest_snapshot", return_value=None):
            executor(pid, res)
        # Should return early

    def test_browser_executor_no_pending_action(self, setup):
        engine, _, _, pid = setup
        executor = BrowserExecutor(engine)
        
        res = MagicMock(action_id="browser.navigate")
        snap = StateSnapshot(snapshot_id="s1", components={BROWSER_ID: {"status": "idle"}})
        with patch.object(engine.repository, "get_latest_snapshot", return_value=snap):
            executor(pid, res)
        # Should return early

    @patch("gradio_chat_agent.execution.browser_executor.sync_playwright")
    def test_browser_executor_unknown_type(self, mock_sync_pw, setup):
        engine, _, _, pid = setup
        executor = BrowserExecutor(engine)
    
        res = MagicMock(action_id="browser.something")
        snap = StateSnapshot(snapshot_id="s1", components={BROWSER_ID: {"status": "busy", "pending_action": {"type": "ghost", "params": {}}}})
        with patch.object(engine.repository, "get_latest_snapshot", return_value=snap):
            executor(pid, res)
        # Should log warning and return

    def test_browser_executor_stop_no_launch(self, setup):
        engine, _, _, _ = setup
        executor = BrowserExecutor(engine)
        executor.stop() # Should not crash

        @patch("gradio_chat_agent.execution.browser_executor.sync_playwright")

        def test_browser_executor_multiple_projects(self, mock_sync_pw, setup):

            engine, _, _, _ = setup

            executor = BrowserExecutor(engine)

            

            mock_pw = mock_sync_pw.return_value.start.return_value

            mock_browser = mock_pw.chromium.launch.return_value

            # Ensure different mocks are returned for each call to new_page

            mock_browser.new_page.side_effect = [MagicMock(name="page1"), MagicMock(name="page2")]

            

            executor._ensure_browser()

            p1 = executor._get_page("p1")

            p2 = executor._get_page("p2")

            

            assert p1 != p2

            assert mock_browser.new_page.call_count == 2

            executor.stop()

    