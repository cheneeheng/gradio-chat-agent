# Chat agent contract — gradio-chat-agent

## Purpose

This document defines the operational contract for the chat agent embedded in gradio-chat-agent: what it may do, how it selects actions, and how it behaves under different execution modes.

---

## Execution modes

### Interactive mode

- **Goal:** Optimize for correctness and user intent confirmation.
- **User confirmation:** Required for actions with `permission.confirmation_required = true`.
- **Ambiguity handling:** If more than one action is plausible or any required parameter is missing, the agent asks one clarifying question and does not execute.
- **Safety behavior:** If preconditions fail, the agent explains the failure and suggests the minimal next action to satisfy preconditions.

### Assisted mode

- **Goal:** Allow multi-step completion with minimal friction while staying auditable.
- **User confirmation:** Still required for `confirmation_required = true`.
- **Ambiguity handling:** If minor parameters are missing and can be safely defaulted (as declared by schema defaults), the agent may proceed; otherwise it asks.
- **Planning:** The agent may propose a short plan of actions before executing the first step when the user request implies multiple dependent steps.

### Autonomous mode

- **Goal:** Execute straightforward, unambiguous sequences end-to-end with strict governance.
- **User confirmation:** Must still be requested for `confirmation_required = true` and for any action marked `permission.risk = "high"`.
- **Ambiguity handling:** The agent must not guess; if ambiguous, it must stop and ask for clarification.
- **Execution limits:** The agent must stop after `max_steps` (configured by the app) and return partial progress with a clear summary.
- **Logging:** Every action attempt must produce an execution result and be logged with intent, inputs, and outcome.

---

## Behavioral rules

- **Registry-only behavior:** The agent must only propose or execute actions present in the action registry.
- **Schema-first parameters:** The agent must construct action inputs that validate against the action schema.
- **State-aware decisions:** The agent must consult the state snapshot before selecting actions, especially for preconditions.
- **No hidden side effects:** The agent must not claim UI changes unless an execution result confirms success.
- **Explainability on failure:** On failure, the agent must return the action attempted, the reason, and what state/precondition blocked it.

---

## Clarification protocol

- **Single-question principle:** Ask the smallest question that resolves execution ambiguity.
- **Choice presentation:** When multiple actions match, present a numbered list of candidate actions by `action_id` and `title`.
- **Parameter completion:** When parameters are missing, ask only for the missing required fields (as defined by schema).

---

## Action permissions and confirmations

- **Permission model:** Each action declares a permission object (see `docs/UI_ACTION_REGISTRY.md`).
- **Confirmation gate:** If `confirmation_required = true`, the agent must request explicit user confirmation (yes/no) before execution.
- **High-risk gate:** If `risk = "high"`, the agent must request confirmation even in autonomous mode.

---

## Required I/O objects

- **Intent object:** Must conform to `docs/schemas/intent.schema.json`.
- **Execution result:** Must conform to `docs/schemas/execution_result.schema.json`.
- **State snapshot:** Must conform to `docs/schemas/state_snapshot.schema.json`.
