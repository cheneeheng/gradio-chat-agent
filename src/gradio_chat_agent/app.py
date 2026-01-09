import os
import sys

# Ensure src is in path
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from gradio_chat_agent.registry.in_memory import InMemoryRegistry
from gradio_chat_agent.persistence.sql_repository import SQLStateRepository
from gradio_chat_agent.execution.engine import ExecutionEngine
from gradio_chat_agent.chat.openai_adapter import OpenAIAgentAdapter
from gradio_chat_agent.ui.layout import create_ui

# Import components/actions
from gradio_chat_agent.registry.system_actions import (
    memory_component, remember_action, remember_handler,
    forget_action, forget_handler
)
from gradio_chat_agent.registry.demo_actions import (
    counter_component, set_action, set_handler,
    increment_action, increment_handler,
    reset_action, reset_handler
)

def main():
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
    db_url = os.environ.get("DATABASE_URL", "sqlite:///gradio_chat_agent.sqlite3")
    print(f"Connecting to database: {db_url}")
    repository = SQLStateRepository(db_url)
    
    # 3. Setup Engine
    engine = ExecutionEngine(registry=registry, repository=repository)
    
    # 4. Setup Agent
    # Note: Requires OPENAI_API_KEY env var
    adapter = OpenAIAgentAdapter()
    
    # 5. Build UI
    demo = create_ui(engine, adapter)
    
    # 6. Launch
    print("Starting Gradio Chat Agent...")
    demo.launch(server_name="0.0.0.0", server_port=7860)

if __name__ == "__main__":
    main()
