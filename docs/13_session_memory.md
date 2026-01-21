# Session Memory (Facts) Management

## Overview

The Agent Layer uses **Session Memory** to maintain context that isn't part of the UI state (e.g., "The user is an expert", "Current project goal is X"). These are stored as "Facts".

---

## Memory Actions

To allow the Agent to manage its own memory, the following actions are reserved in the registry:

### `memory.remember`
*   **Purpose**: Persist a key-value pair for future turns.
*   **Inputs**: `{"key": "string", "value": "any"}`
*   **Engine Logic**: Upserts the fact in the `session_facts` table scoped to the project.

### `memory.forget`
*   **Purpose**: Remove a previously stored fact.
*   **Inputs**: `{"key": "string"}`
*   **Engine Logic**: Deletes the row from `session_facts`.

---

## Fact Injection (The Agent Loop)

1.  **Read Path**: At the start of every chat turn, the Agent Adapter fetches all facts for the current `(user_id, project_id)`.
2.  **Context**: Facts are injected into the LLM system prompt as a "Memory Block".
3.  **Update Path**: If the LLM determines a piece of info is worth keeping, it proposes a `memory.remember` intent.

---

## Scope & Security

*   **Privacy**: Facts are strictly scoped to the `ProjectID`. User A cannot see facts stored by User B unless they are in the same Project.
*   **Lifecycle**: Facts persist until explicitly forgotten or the project is deleted.
