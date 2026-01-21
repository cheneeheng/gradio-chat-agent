# Persistence Layer Architecture

## Overview

The persistence layer manages the storage of application state, execution history, and configuration. It is designed to support the **"Single Source of Truth"** principle, where the database state allows for full reconstruction of the application's history (Time Travel / Replay).

---

## Data Model (Conceptual)

While the implementation may use SQLite (for local) or PostgreSQL (for prod), the conceptual schema is as follows:

### 1. Identity & Access
*   **Users**: `id`, `username`, `password_hash`, `created_at`
*   **Projects**: `id`, `name`, `created_at`, `archived_at`
*   **ProjectMemberships**: `user_id`, `project_id`, `role` (viewer/operator/admin)

### 2. State & History
*   **Snapshots**:
    *   `id`: unique ID (e.g., UUID or hash)
    *   `project_id`: FK to Projects
    *   `timestamp`: When state was captured
    *   `components`: JSON blob of the entire UI state (Heavy, but simple. Optimization: Store diffs and periodical full snapshots).
*   **Executions** (The Audit Log):
    *   `id`: Sequence number
    *   `project_id`: FK to Projects
    *   `request_id`: ID of the initiating intent
    *   `action_id`: The action attempted
    *   `status`: success/rejected/failed
    *   `inputs`: JSON blob of arguments
    *   `state_diff`: JSON blob of the delta applied
    *   `snapshot_id`: FK to the resulting snapshot
    *   `metadata`: Cost, execution time, user_id

### 3. Governance
*   **ProjectLimits**:
    *   `project_id`
    *   `daily_budget`: Integer
    *   `rate_limit_minute`: Integer
*   **ActionBudgets**: Per-action cost tracking.

### 4. Automation & Integration
*   **Webhooks**:
    *   `id`
    *   `project_id`: FK to Projects
    *   `secret`: Signing secret for verification
    *   `action_id`: The action to execute
    *   `inputs_template`: Template to map payload to action inputs
*   **Schedules**:
    *   `id`
    *   `project_id`: FK to Projects
    *   `action_id`: The action to execute
    *   `cron`: Cron expression
    *   `inputs_json`: Static inputs for the job
    *   `enabled`: Boolean


---

## State Management Strategy

### Snapshotting vs Event Sourcing
The system uses a **Snapshot-Heavy** approach with diff logging.
*   **Read Path**: The agent needs the *full* current state to make decisions. Loading the latest snapshot is O(1).
*   **Write Path**: Every execution writes a full snapshot. This is storage-intensive but simplest for consistency.
*   **Audit Path**: The `Executions` table acts as an event log. We store `state_diff` for UI visualization and human auditing, but technically the Snapshots are authoritative.

### Replayability
To replay a session:
1.  Load the initial snapshot (or empty state).
2.  Fetch all `ExecutionResult` records where `status=success`, ordered by time.
3.  Re-apply the `state_diff` (or re-execute the handler, if deterministic) sequentially.
4.  Verify the final state matches the current state.

---

## Concurrency & Locking

To ensure the "Single Source of Truth":
*   **Project-Scope Locking**: The persistence repository (or the Engine utilizing it) must enforce that only one transaction writes to a `project_id` at a time.
*   In SQLite: Implicit via the single-writer lock.
*   In Postgres: Explicit `SELECT FOR UPDATE` on the Project row or an advisory lock.

---

## Session Memory (Short-Term)

Distinct from the "Application State" (which drives the UI), the Agent has "Session Memory".
*   **Facts Table**: Stores key-value pairs derived from the chat conversation that aren't UI state (e.g., "User prefers dark mode" or "User is working on Q3 report").
*   **Scope**: Scoped to `(user_id, project_id)`.
