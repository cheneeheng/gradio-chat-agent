# Chat control protocol — gradio-chat-agent

## Purpose

This document defines the structured protocol between the chat agent and the execution engine. It standardizes how the agent proposes or executes actions and how the system responds.

This protocol is implementation-agnostic and is designed to support:

- action replay
- deterministic testing
- audit logs
- alternate chat frontends

---

## Canonical objects

- **Intent:** The agent’s structured request to perform an action (or ask a clarification).
  - **Schema:** `docs/schemas/intent.schema.json`
- **State snapshot:** Read-only view of current application/component state.
  - **Schema:** `docs/schemas/state_snapshot.schema.json`
- **Execution result:** Output of attempting an action.
  - **Schema:** `docs/schemas/execution_result.schema.json`

---

## Interaction patterns

### Action execution

- **Step 1:** Agent reads current state snapshot.
- **Step 2:** Agent produces an intent with `type = "action_call"`.
- **Step 3:** Engine validates intent against registry schemas and preconditions.
- **Step 4:** Engine returns execution result + updated state snapshot.

### Clarification request

- **When used:** Missing required parameters or ambiguous action selection.
- **Mechanism:** Agent produces an intent with `type = "clarification_request"` and a `question`.
- **Engine behavior:** No mutation occurs; state snapshot is unchanged.

### Confirmation request

- **When used:** `confirmation_required = true` or `risk = "high"`.
- **Mechanism:** Agent asks for confirmation in chat; on approval, it re-issues the same `action_call` with `confirmed = true`.
- **Engine behavior:** Engine must reject confirmed-required actions when `confirmed != true`.

---

## Logging requirements

- **Intent logging:** Store the full intent object for every attempted step.
- **Result logging:** Store the execution result, including failures.
- **Snapshot logging:** Store either the full state snapshot or a diff; but execution_result must include `state_diff` when feasible.
