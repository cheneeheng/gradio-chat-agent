# FAQ

## What is the difference between Session Memory and Session Facts?

The Gradio Chat Agent distinguishes between these two concepts based on their scope, versioning, and how the agent interacts with them.

### 1. Session Memory (`sys.memory`)
*   **Definition:** A specific **Component** defined in the application state.
*   **Location:** Defined in `src/gradio_chat_agent/registry/system_actions.py` as `memory_component` with ID `sys.memory`.
*   **Scope:** **Project-Wide (Shared)**. Since it lives in the `StateSnapshot`, it is shared by all users interacting with that project state.
*   **Behavior:** It is **Transactional and Versioned**. Changes to memory are recorded as state transitions (snapshots) with diffs.
*   **Access:** Modified by the Agent via specific actions: `memory.remember` and `memory.forget`.

### 2. Session Facts (Repository Layer)
*   **Definition:** A **Persistence Utility** method exposed by the `StateRepository` interface.
*   **Location:** Defined in `src/gradio_chat_agent/persistence/repository.py` (methods `save_session_fact`, `get_session_facts`).
*   **Scope:** **User-Specific**. The storage key is generated using both `project_id` and `user_id`.
*   **Behavior:** It is a **Simple Key-Value Store** separate from the main state machine history. It is not versioned.
*   **Access:** Direct repository calls. This is typically used for user-specific preferences or long-term recall that doesn't need to be part of the shared project state.

### Summary Table

| Feature | Session Memory (`sys.memory`) | Session Facts (Repository) |
| :--- | :--- | :--- |
| **Type** | Application State Component | Persistence Layer Data |
| **Scope** | **Project** (Shared State) | **User** (Personalized) |
| **Versioning** | Yes (Snapshots & Diffs) | No (Current Value Only) |
| **Agent Access**| Via Actions (`remember`/`forget`) | Direct Repo Access |
| **Primary Use**| Active context for the conversation | Long-term user data / Preferences |

## How does the Agent handle automated tasks or background jobs?

Automated tasks are managed by the **Scheduler Worker**, which allows for non-interactive state mutations based on time (Cron expressions).

*   **Engine Integration:** The scheduler polls the persistence layer for enabled schedules and registers them with an internal `APScheduler` instance.
*   **System Identity:** Actions triggered by the scheduler execute using a dedicated **"System" user** (`system_scheduler`) with `admin` permissions. This ensures they can bypass interactive confirmation gates while remaining fully auditable.
*   **Traceability:** Scheduled executions are recorded in the standard Audit Log with a special `trace` metadata indicating they were triggered by a schedule.

## Where can I find system metrics, and are they user-specific?

The application exposes operational metrics for infrastructure-level monitoring (e.g., Prometheus/Grafana).

*   **Metrics Endpoint:** Metrics are served in Prometheus format at the `/metrics` endpoint. This is made possible by mounting the Gradio UI inside a **FastAPI** application.
*   **Global/Project Scope:** Metrics (like execution counts, latency, and budget usage) are aggregated at the **Global** or **Project** level.
*   **Cardinality Control:** Metrics are **not** user-specific by design. Adding individual `user_id` labels to time-series data would lead to "metric explosion" (high cardinality), which degrades the performance of monitoring systems.
*   **User Attribution:** For detailed per-user accounting or security audits, you should refer to the **Audit Log** (SQL) or the **Structured Logs** (JSONL), which are designed to handle high-cardinality data efficiently.

