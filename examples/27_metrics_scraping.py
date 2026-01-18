"""Example of Metrics Scraping and Verification.

This example demonstrates:
1. Performing actions that trigger metric updates.
2. Generating and inspecting the metrics output in Prometheus format.
"""

from gradio_chat_agent.execution.engine import ExecutionEngine
from gradio_chat_agent.persistence.in_memory import InMemoryStateRepository
from gradio_chat_agent.registry.in_memory import InMemoryRegistry
from gradio_chat_agent.registry.demo_actions import counter_component, set_action, set_handler
from gradio_chat_agent.observability.metrics import get_metrics_content
from gradio_chat_agent.models.intent import ChatIntent
from gradio_chat_agent.models.enums import IntentType

def run_example():
    # 1. Setup system
    registry = InMemoryRegistry()
    repository = InMemoryStateRepository()
    engine = ExecutionEngine(registry, repository)
    
    registry.register_component(counter_component)
    registry.register_action(set_action, set_handler)
    
    project_id = "metrics-demo"
    
    print(f"--- Scenario: Triggering Metric Updates ---")
    
    # 2. Perform some actions
    for i in range(3):
        intent = ChatIntent(
            type=IntentType.ACTION_CALL,
            request_id=f"req-{i}",
            action_id="demo.counter.set",
            inputs={"value": i * 10}
        )
        engine.execute_intent(project_id, intent)
    
    # 3. Get metrics content
    metrics_str = get_metrics_content()
    
    print("\nPrometheus Metrics Output (Subset):")
    for line in metrics_str.splitlines():
        if "engine_execution_total" in line or "budget_consumption_total" in line:
            print(line)

if __name__ == "__main__":
    run_example()
