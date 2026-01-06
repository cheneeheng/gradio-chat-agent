# gradio-chat-agent

A pure-Python Gradio app where a floating chat interface acts as a governed control plane for UI components.

Instead of letting chat “poke” UI elements directly, the app exposes explicit component + action registries. The agent converts user requests into structured intent objects, which are validated and executed by an engine that returns a structured result and an updated state snapshot.

---

## Why this exists

- **Chat-controlled UI without prompt spaghetti:** UI behavior is declared via registries and schemas.
- **Deterministic execution:** Natural language becomes structured intent; execution consumes data, not vibes.
- **Auditability:** Every action attempt produces an execution result and can be logged/replayed.

---

## Repository structure

- **src/gradio_chat_agent:** Application code (pure Python package).
- **docs:** Planning + governance documentation.
- **docs/schemas:** JSON Schemas for intent, actions, components, snapshots, and execution results.

---

## Core concepts

- **Component registry:** Declares what exists in the UI and the state shape of each component.
- **Action registry:** Declares what can happen, including inputs, preconditions, effects, and permission gates.
- **Intent object:** The agent’s structured request to execute an action or ask a clarification.
- **Execution engine:** Validates, checks preconditions, applies state mutation, and returns an execution result.
- **State snapshot:** Read-only state presented back to the agent for the next turn.

---

## Execution modes

The agent supports three execution modes (defined in `docs/CHAT_AGENT_CONTRACT.md`):

- **Interactive:** Ask clarifying questions and confirm gated actions.
- **Assisted:** Defaults safe values when declared by schemas; still confirms gated/high-risk actions.
- **Autonomous:** Executes unambiguous sequences with strict stopping and logging rules.

---

## Docs

- **docs/ARCHITECTURE.md:** System overview and flows.
- **docs/CHAT_AGENT_CONTRACT.md:** Agent behavior + execution modes.
- **docs/UI_COMPONENT_REGISTRY.md:** Component declaration contract.
- **docs/UI_ACTION_REGISTRY.md:** Action declaration contract.
- **docs/CHAT_CONTROL_PROTOCOL.md:** Intent/result protocol and logging rules.
- **docs/schemas/\*.json:** Canonical JSON Schemas.

---

## Next implementation steps

- **Implement registries:** Represent component/action registries in Python (or JSON) and load them at startup.
- **Implement state store:** Central state object + snapshot creation.
- **Implement execution engine:** Validate intent, enforce permissions and preconditions, apply mutations, emit diffs.
- **Integrate floating chatbot:** The chat UI produces intents and renders execution results and state-based context.

If you tell me what your floating chatbot exposes (callbacks/events and expected data), I can align the protocol boundary precisely.
