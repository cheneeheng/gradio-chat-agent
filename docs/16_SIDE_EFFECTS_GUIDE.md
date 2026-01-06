# Real-World Integration (Side Effects)

## Overview

The `gradio-chat-agent` acts as a **Governed Control Plane**. While its primary internal work is pure state mutation (updating snapshots), its purpose is often to control real-world systems.

This document describes the recommended patterns for integrating side effects while preserving the system's core guarantees of **Auditability** and **Replayability**.

---

## The Side-Effect Pattern

Side effects should never be performed directly inside an `ActionHandler`. Handlers must remain pure to allow state reconstruction during a Replay.

Instead, use the **Reconciliation Pattern**:

1.  **Intent**: User requests "Turn on the furnace".
2.  **State Mutation**: The engine executes the handler, setting `components.furnace.power = "on"`.
3.  **Commit**: The engine saves the new snapshot and audit log.
4.  **Side Effect (Post-Commit)**: An observer (or the engine's `post_execution` hook) sees the successful commit and dispatches the actual command to the furnace hardware.

---

## Implementation Strategies

### 1. Engine Post-Execution Hooks (Synchronous)
For simple, fast side effects (e.g., calling a REST API), the engine can trigger a hook immediately after the database commit.

*   **Pros**: Simple to implement.
*   **Cons**: Blocks the engine's response until the side effect completes.

### 2. State Observers (Asynchronous)
For long-running or unreliable side effects, use a background worker that "watches" the state or the audit log.

*   **Pros**: Does not block the UI; naturally handles retries.
*   **Cons**: Requires a task queue (e.g., Redis + Celery/TaskIQ).

---

## Safety & Replay

**Crucial Rule**: Side effects must be suppressed during a **Replay** or **Simulation**.

When the engine is in `replay` mode:
1.  Handlers are executed to reconstruct state.
2.  Post-execution hooks are **skipped**.
3.  Observers must check the `execution_context.mode` before acting.

This ensures that replaying a year's worth of history doesn't re-trigger a year's worth of real-world actions.
