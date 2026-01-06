# UI component registry — gradio-chat-agent

## Purpose

This document defines the contract for declaring UI components that the chat agent can observe and affect indirectly (through actions). It is a conceptual registry; the implementation can be Python, JSON, YAML, or code-driven, but the schema is fixed.

- **Schema:** `docs/schemas/component.schema.json`
- **Snapshot schema:** `docs/schemas/state_snapshot.schema.json`

---

## Component model

Each component declaration must include:

- **component_id:** Stable identifier used by actions and state snapshots.
- **title:** Human-readable short name.
- **description:** What the component represents and how users expect it to behave.
- **state_schema:** JSON Schema describing the component’s state shape.
- **permissions:** Read/write capabilities for the agent (via actions, never direct mutation).
- **invariants:** Constraints that must always hold (enforced by preconditions/actions).

---

## Example components

### Example: model selector

- **component_id:** `model.selector`
- **State:** Which model is selected and whether it is loaded.
- **Notes:** Many actions should require `loaded = true` before execution.

### Example: prompt editor

- **component_id:** `prompt.editor`
- **State:** Current prompt text, template variables, and last edit timestamp.

### Example: output panel

- **component_id:** `output.panel`
- **State:** Latest response, streaming status, and metadata (tokens, latency).

---

## Agent expectations

- **No direct mutation:** The agent does not set component state directly; it requests actions.
- **State observability:** The agent may read the state snapshot to decide which action to run next.
- **Stable identifiers:** component_id values must be stable over time to preserve replayability and logs.

---

## Implementation notes

- **Rendering:** Gradio components should render from the central state (single source of truth).
- **Updates:** UI updates should be a function of state, not of chat messages.
