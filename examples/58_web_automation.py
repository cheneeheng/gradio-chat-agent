"""Example of using the Web Automation Suite.

This example demonstrates how to:
1. Register web automation components and actions.
2. Initialize the execution engine and browser executor.
3. Perform web automation tasks (navigate, click, type).
4. Observe state synchronization.
"""

import time
import uuid
from gradio_chat_agent.execution.engine import ExecutionEngine
from gradio_chat_agent.execution.observer import AuditLogObserver
from gradio_chat_agent.execution.browser_executor import BrowserExecutor
from gradio_chat_agent.persistence.in_memory import InMemoryStateRepository
from gradio_chat_agent.registry.in_memory import InMemoryRegistry
from gradio_chat_agent.registry.web_automation import (
    browser_component,
    navigate_action, navigate_handler,
    click_action, click_handler,
    type_action, type_handler,
    scroll_action, scroll_handler,
    sync_browser_state_action, sync_browser_state_handler
)
from gradio_chat_agent.models.intent import ChatIntent
from gradio_chat_agent.models.enums import IntentType, ExecutionMode

def run_example():
    # 1. Setup system
    registry = InMemoryRegistry()
    repository = InMemoryStateRepository()
    engine = ExecutionEngine(registry, repository)
    
    # Register components and actions
    registry.register_component(browser_component)
    registry.register_action(navigate_action, navigate_handler)
    registry.register_action(click_action, click_handler)
    registry.register_action(type_action, type_handler)
    registry.register_action(scroll_action, scroll_handler)
    registry.register_action(sync_browser_state_action, sync_browser_state_handler)
    
    project_id = "browser-demo"
    repository.create_project(project_id, "Browser Demo")
    
    # 2. Setup Browser Automation Observer
    browser_executor = BrowserExecutor(engine)
    # Fast polling for demo
    browser_observer = AuditLogObserver(engine, poll_interval=1.0)
    browser_observer.add_callback(browser_executor)
    
    browser_observer.start()
    
    try:
        print("--- Step 1: Navigating to Google ---")
        nav_intent = ChatIntent(
            type=IntentType.ACTION_CALL,
            request_id=str(uuid.uuid4()),
            action_id="browser.navigate",
            inputs={"url": "https://www.google.com"},
            execution_mode=ExecutionMode.AUTONOMOUS
        )
        engine.execute_intent(project_id, nav_intent, user_roles=["admin"])
        
        print("Navigation queued. Waiting for executor to process...")
        # Poll state until it's idle again
        for _ in range(10):
            time.sleep(1)
            snapshot = repository.get_latest_snapshot(project_id)
            state = snapshot.components.get("browser", {})
            print(f"Current Browser URL: {state.get('url')} (Status: {state.get('status')})")
            if state.get("status") == "idle" and state.get("url") != "about:blank":
                print(f"Successfully reached: {state.get('title')}")
                break
        
        print("\n--- Step 2: Typing into Search Box ---")
        # Google search box usually has name="q" or similar, but for demo let's assume we know a selector
        # On Google, the search textarea often has class 'gLFyf'
        type_intent = ChatIntent(
            type=IntentType.ACTION_CALL,
            request_id=str(uuid.uuid4()),
            action_id="browser.type",
            inputs={"selector": "textarea[name='q']", "text": "Playwright Python"},
            execution_mode=ExecutionMode.AUTONOMOUS
        )
        engine.execute_intent(project_id, type_intent, user_roles=["admin"])
        
        print("Type action queued...")
        time.sleep(3) # Wait for processing and sync
        
        snapshot = repository.get_latest_snapshot(project_id)
        state = snapshot.components.get("browser", {})
        print(f"Last Action Result: {state.get('last_action_result')}")

    except Exception as e:
        print(f"Example failed: {str(e)}")
    finally:
        browser_observer.stop()
        browser_executor.stop()

if __name__ == "__main__":
    run_example()
