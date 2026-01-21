"""Example of Custom Business Metrics in Action Handlers.

This example demonstrates how to:
1. Define custom Prometheus metrics.
2. Update those metrics from within a registered action handler.
3. Verify the metrics appear in the system registry.
"""

from prometheus_client import Counter
from gradio_chat_agent.execution.engine import ExecutionEngine
from gradio_chat_agent.persistence.in_memory import InMemoryStateRepository
from gradio_chat_agent.registry.in_memory import InMemoryRegistry
from gradio_chat_agent.models.action import ActionDeclaration, ActionPermission
from gradio_chat_agent.models.intent import ChatIntent
from gradio_chat_agent.models.enums import IntentType, ActionRisk, ActionVisibility
from gradio_chat_agent.observability.metrics import get_metrics_content, REGISTRY

# 1. Define a business-level metric
# We register it to the system REGISTRY so it shows up in the /metrics endpoint
ITEMS_PROCESSED_TOTAL = Counter(
    "business_items_processed_total",
    "Total count of items processed by the business logic.",
    ["item_type"],
    registry=REGISTRY
)

def run_example():
    registry = InMemoryRegistry()
    repository = InMemoryStateRepository()
    engine = ExecutionEngine(registry, repository)
    project_id = "metrics-biz-demo"

    # 2. Register an action that updates the custom metric
    def process_items_handler(inputs, snapshot):
        count = inputs.get("count", 1)
        item_type = inputs.get("item_type", "generic")
        
        # Logic: Increment the business counter
        ITEMS_PROCESSED_TOTAL.labels(item_type=item_type).inc(count)
        
        return {}, [], f"Processed {count} {item_type} items."

    registry.register_action(
        ActionDeclaration(
            action_id="biz.process",
            title="Process Items",
            description="Simulates processing items and updates metrics.",
            targets=["sys"],
            input_schema={
                "type": "object",
                "properties": {
                    "count": {"type": "integer"},
                    "item_type": {"type": "string"}
                }
            },
            permission=ActionPermission(confirmation_required=False, risk=ActionRisk.LOW, visibility=ActionVisibility.USER)
        ),
        handler=process_items_handler
    )

    # 3. Execute the action
    print("--- Executing Business Actions ---")
    engine.execute_intent(project_id, ChatIntent(
        type=IntentType.ACTION_CALL, request_id="r1", 
        action_id="biz.process", inputs={"count": 5, "item_type": "widget"}
    ))
    engine.execute_intent(project_id, ChatIntent(
        type=IntentType.ACTION_CALL, request_id="r2", 
        action_id="biz.process", inputs={"count": 10, "item_type": "gadget"}
    ))

    # 4. Verify in the Prometheus output
    print("\n--- Verifying Custom Business Metrics ---")
    metrics_str = get_metrics_content()
    for line in metrics_str.splitlines():
        if "business_items_processed_total" in line:
            print(line)

if __name__ == "__main__":
    run_example()
