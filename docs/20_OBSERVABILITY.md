# Observability Guide

Effective operation of the `gradio-chat-agent` requires visibility into three distinct layers: the authoritative Audit Log, operational Application Logs, and Runtime Metrics.

## 1. Audit Log (Business Record)

The **Audit Log** is the persistent, immutable history of *what happened to the state*. It is stored in the database (`executions` table) and is accessible via the API (`api_get_audit_log`).

*   **Purpose**: Compliance, Replay, User History.
*   **Format**: Structured JSON (see `docs/schemas/execution_result.schema.json`).
*   **Key Fields**:
    *   `request_id`: Trace ID.
    *   `status`: `success` | `rejected` | `failed`.
    *   `state_diff`: Exact changes made.
    *   `metadata`: User ID, Cost.

## 2. Application Logs (Operational Debugging)

**Application Logs** are emitted to `stdout`/`stderr` by the container. These are for SREs/Developers to diagnose runtime issues (DB connection failures, unhandled exceptions, latency).

*   **Format**: JSON-structured lines (JSONL) are recommended for production ingestion (Splunk/Datadog).
*   **Levels**:
    *   `ERROR`: System cannot proceed (e.g., DB down).
    *   `WARNING`: Recoverable issue (e.g., LLM rate limit, webhook delivery failure).
    *   `INFO`: High-level lifecycle events (Startup, Project Created).
    *   `DEBUG`: detailed trace of the Agent loop (LLM raw inputs/outputs).

### Example Log Entry
```json
{
  "timestamp": "2023-10-27T10:00:00Z",
  "level": "INFO",
  "component": "execution_engine",
  "event": "execution_completed",
  "project_id": 42,
  "action_id": "demo.counter.set",
  "status": "success",
  "duration_ms": 45
}
```

## 3. Metrics (Prometheus)

The application should expose a `/metrics` endpoint (via `prometheus_client`) for scraping.

### Key Indicators

| Metric Name | Type | Labels | Description |
| :--- | :--- | :--- | :--- |
| `engine_execution_total` | Counter | `status`, `action_id`, `project_id` | Count of executed intents. |
| `engine_execution_duration_seconds` | Histogram | `action_id` | Latency of the execution pipeline. |
| `budget_consumption_total` | Counter | `project_id` | Abstract budget units consumed. |
| `llm_token_usage_total` | Counter | `model` | Tokens used by the Agent layer. |
| `active_projects` | Gauge | - | Number of projects with recent activity. |

## Alerting Rules

Recommended alerts for PagerDuty/OpsGenie:

1.  **High Failure Rate**: `rate(engine_execution_total{status="failed"}[5m]) > 5%`
2.  **Budget Exhaustion**: `budget_used / budget_limit > 90%` (User-facing alert, not necessarily SRE).
3.  **LLM Latency**: `histogram_quantile(0.95, engine_execution_duration_seconds) > 10s` (Indicates LLM timeout or slow handler).
