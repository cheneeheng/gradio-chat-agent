# UI action registry — gradio-chat-agent

## Purpose

This document defines the contract for actions that can be executed to mutate application state and thereby control UI components.

- **Schema:** `docs/schemas/action.schema.json`
- **Intent schema:** `docs/schemas/intent.schema.json`
- **Execution result schema:** `docs/schemas/execution_result.schema.json`

---

## Action model

Each action declaration must include:

- **action_id:** Stable identifier used by intent and logs.
- **title:** Human-readable short label.
- **description:** What the action does, in user terms.
- **targets:** Component IDs affected by the action.
- **input_schema:** JSON Schema for the action call parameters.
- **preconditions:** Machine-checkable conditions over the current state snapshot.
- **effects:** What state fields may change (for auditability and UI diffs).
- **permission:** Confirmation and risk metadata.

---

## Permission contract

- **confirmation_required:** If true, the agent must ask the user to confirm before running.
- **risk:** One of `low | medium | high`. High always requires confirmation (even in autonomous mode).
- **visibility:** One of `user | developer`. Developer visibility actions are hidden from normal UI affordances but still registry-declared.

---

## Examples of typical actions

### Example: select model

- **action_id:** `model.select`
- **Targets:** `model.selector`
- **Inputs:** `{ "model_name": "string" }`
- **Preconditions:** Model name must exist in available models.
- **Permission:** low risk, no confirmation.

### Example: load model

- **action_id:** `model.load`
- **Targets:** `model.selector`
- **Inputs:** optional load options.
- **Preconditions:** A model must be selected.
- **Permission:** medium risk, may require confirmation depending on resource cost.

### Example: run inference

- **action_id:** `inference.run`
- **Targets:** `prompt.editor`, `output.panel`
- **Inputs:** prompt overrides, generation params.
- **Preconditions:** Model must be loaded; output must not be currently streaming (unless supported).
- **Permission:** medium risk, confirmation usually not required.

---

## Registry completeness rules

- **No hidden behavior:** If the UI can change state due to chat, there must be a corresponding action.
- **No action without schema:** Every action must have an input schema, even if empty.
- **No action without preconditions:** Preconditions can be empty, but must exist as a field for uniformity.
