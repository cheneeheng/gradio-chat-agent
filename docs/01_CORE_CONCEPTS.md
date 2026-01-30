# Core Concepts — gradio-chat-agent

## Why This Project Exists

Traditional "chat-controls-UI" implementations often suffer from several flaws that this project aims to solve:

- **Prompt Spaghetti:** Avoiding complex, fragile prompts to describe UI behavior by using explicit registries and schemas.
- **Vibe-based Execution:** Moving away from letting the LLM "guess" how to mutate state. Instead, natural language is converted into structured intent that the engine executes deterministically.
- **Lack of Auditability:** Providing a full audit trail where every action attempt produces a structured result and can be logged or replayed.

---

## The Core Model

The system is built around five primary pillars:

1.  **Component Registry:** A declarative catalog of what exists in the UI and the state shape of each component.
2.  **Action Registry:** A declarative catalog of what can happen, including inputs, preconditions, effects, and permission gates.
3.  **Intent Object:** The agent’s structured request to execute an action or ask a clarification.
4.  **Execution Engine:** A deterministic validator and executor that checks permissions/preconditions and applies state mutations.
5.  **State Snapshot:** A read-only representation of the current state presented back to the agent for the next turn.

---

## Execution Philosophy

The agent acts as a **control plane**, not a direct driver. It proposes plans, but the execution engine remains the sole authority for state mutation.

- **Deterministic:** The same intent in the same state always yields the same result.
- **Safe:** Permissions are enforced at the engine level, not the prompt level.
- **Auditable:** Every state change is a logged event.
