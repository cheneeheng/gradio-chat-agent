"""Prometheus metrics for the Gradio Chat Agent."""

from prometheus_client import Counter, Histogram, Gauge, CollectorRegistry, generate_latest, CONTENT_TYPE_LATEST

# Define metrics
REGISTRY = CollectorRegistry()

ENGINE_EXECUTION_TOTAL = Counter(
    "engine_execution_total",
    "Total count of executed intents.",
    ["status", "action_id", "project_id"],
    registry=REGISTRY
)

ENGINE_EXECUTION_DURATION_SECONDS = Histogram(
    "engine_execution_duration_seconds",
    "Latency of the execution pipeline.",
    ["action_id"],
    registry=REGISTRY
)

BUDGET_CONSUMPTION_TOTAL = Counter(
    "budget_consumption_total",
    "Abstract budget units consumed.",
    ["project_id"],
    registry=REGISTRY
)

LLM_TOKEN_USAGE_TOTAL = Counter(
    "llm_token_usage_total",
    "Tokens used by the Agent layer.",
    ["model"],
    registry=REGISTRY
)

ACTIVE_PROJECTS = Gauge(
    "active_projects",
    "Number of projects with recent activity.",
    registry=REGISTRY
)

def get_metrics_content():
    """Generates the latest metrics in Prometheus format."""
    return generate_latest(REGISTRY).decode("utf-8")
