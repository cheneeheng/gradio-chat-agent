# Automation System (Webhooks & Schedules)

## Overview

Beyond the interactive Chat UI, the `gradio-chat-agent` supports two non-interactive execution triggers: **Webhooks** (external push) and **Schedules** (time-based pull).

---

## Webhook Execution Flow

1.  **Ingress**: An external system sends an HTTP POST to `/api/api_webhook_execute/<webhook_id>`.
2.  **Verification**: The engine validates the `X-Hub-Signature` (or similar) using the Webhook's registered `secret`.
3.  **Resolution**:
    *   The engine retrieves the `inputs_template` (Jinja2 or similar).
    *   The incoming JSON payload is used to render the template into a structured `inputs` dictionary.
4.  **Implicit Intent**: The engine creates an internal `ChatIntent` with `type="action_call"` and `execution_mode="autonomous"`.
5.  **Execution**: The engine processes the intent as a standard authoritative user.

---

## Schedule Execution Flow

1.  **The Scheduler Worker**: A background process (e.g., `APScheduler`) runs alongside the app container.
2.  **Trigger**: When a CRON expression matches the current time:
    *   The worker retrieves the `action_id` and `inputs_json` from the `schedules` table.
3.  **Execution**: The worker calls the `api_execute_action` endpoint internally using a "System" user identity.

---

## Safety & Rate Limits

*   **Quota Integration**: Both Webhooks and Schedules consume the project's `daily_budget`.
*   **Concurrency**: Automated actions compete for the project lock just like human users.
*   **Auditability**: Records are logged with `metadata.trigger = "webhook"` or `"schedule"`.
