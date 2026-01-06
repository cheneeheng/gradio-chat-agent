# Troubleshooting Guide

Common issues and resolution strategies for `gradio-chat-agent`.

## 1. Execution Blocked (Status: Rejected)

**Symptom**: User requests an action, but the chat responds with "Rejected" or "Permission Denied".

*   **Cause 1: Role Mismatch**
    *   *Check*: Does the user have the role required by the action?
    *   *Fix*: Admin must grant the role or use an alternative action.
*   **Cause 2: Budget Exceeded**
    *   *Check*: Check `api_budget_forecast`.
    *   *Fix*: Wait for daily reset or admin manually increases budget via `project.update_limits`.
*   **Cause 3: Precondition Failure**
    *   *Check*: Read the `detail` in the error message (e.g., "Model must be loaded").
    *   *Fix*: User must perform the prerequisite action (e.g., "Load model") first.

## 2. Execution Stuck (Status: Pending Approval)

**Symptom**: Action returns "Pending Approval" and state does not change.

*   **Cause**: The action cost or risk level triggered a governance rule.
*   **Fix**: An Admin must review the request (via a specialized UI or API) and re-submit it with explicit override or approval.

## 3. "I can't do that" (Agent Refusal)

**Symptom**: The LLM refuses to propose an action even though it exists.

*   **Cause**: The System Prompt or Registry Injection might be truncated if the context window is full.
*   **Fix**: Check `llm_token_usage`. Reduce the number of visible actions or history length.

## 4. Database Locking / Timeout

**Symptom**: Application logs show `DatabaseLockedError` or high latency.

*   **Cause**: SQLite handling concurrent writes from multiple threads/workers.
*   **Fix**: Switch to PostgreSQL for production concurrency. Ensure `WAL` mode is enabled if sticking with SQLite (`PRAGMA journal_mode=WAL;`).

## 5. State Desync

**Symptom**: The UI shows data that conflicts with the Chat response.

*   **Cause**: A handler mutated state but the UI didn't refresh, or the Snapshot failed to save.
*   **Fix**: Refresh the page (reloads from DB). Check Application Logs for "Commit failed".
