# Architecture — gradio-chat-agent

## Overview

gradio-chat-agent is a pure-Python Gradio application where a conversational agent acts as a control plane for UI components.

The chat interface does not manipulate Gradio components directly. Instead, it operates through explicit registries (components + actions), structured intent objects, and a governed execution engine that validates, applies, and reports state mutations.

---

## Core principle

- **Contracts, not inference:** The agent only uses declared actions/components; it must not invent operations.
- **Determinism, not heuristics:** Natural language is converted to a structured intent object; execution consumes structured data, not free text.
- **Auditability, not convenience:** Every attempted action yields a structured result and can be logged/replayed.

---

## System Flow (Bidirectional)

```
User
  ↓
Chat Interface (Floating Chatbot)
  ↓
Structured Intent Object
  ↓
Action Resolver
  ↓
Execution Engine
  ↓
Component State Mutation
  ↓
Gradio UI Update
  ↑
State Snapshot / Action Result
  ↑
Chat Interface (Context for next turn)
```

The chatbot never touches UI objects directly.

This bidirectional flow makes explicit that state and execution results feed back into the chat, enabling multi-step reasoning, correction, and planning.

---

## System Flow (Numbered)

```
1. User submits a message via the chat interface
2. Chat interface produces a structured intent object
3. Intent resolver maps intent to a candidate action
4. Action is validated against schemas and preconditions
5. Execution engine applies the state mutation
6. Gradio UI updates based on new component state
7. Updated state and execution result are returned to chat
```

This representation is intended for documentation, onboarding, and design reviews.

---

## System Flow (Diagram)

```Mermaid
flowchart TD
    U[User]
    C[Chat Interface<br/>(Floating Chatbot)]
    I[Structured Intent]
    R[Action Resolver]
    E[Execution Engine]
    S[Component State Mutation]
    UI[Gradio UI Update]

    U --> C
    C --> I
    I --> R
    R --> E
    E --> S
    S --> UI
    UI --> C
```

---

## Runtime building blocks

### Registries

- **Component registry:** Declares what UI components exist, their state shapes, and permissions.
- **Action registry:** Declares what actions can be executed, their input schema, targets, preconditions, and permission level.

### State model

- **Single source of truth:** A central application state object backs all UI rendering.
- **Snapshots:** The agent reads a read-only state snapshot; it never reads Gradio objects.
- **Mutations:** All changes happen via actions executed by the execution engine.

### Execution pipeline

- **Resolve:** Convert intent to an action call (or a clarification request).
- **Validate:** JSON-schema validation + precondition checks.
- **Execute:** Apply mutation and produce a structured execution result.
- **Report:** Return updated state snapshot + result to chat.

---

## Key invariants

- **No direct UI mutation from chat:** Chat does not call Gradio components; it calls actions.
- **No hidden actions:** Only actions in the registry may run.
- **No ambiguous execution:** If multiple actions match, the system must request clarification or require explicit disambiguation.

---

## FINAL ARCHITECTURE

The system is structured as a **governed execution control plane** with a chat interface as one of its clients.

```
┌──────────────────────────────────────┐
│              Chat UI                 │
│        (Gradio Chat Interface)       │
│                                      │
│  - User messages                     │
│  - Plan previews                     │
│  - Approval / rejection              │
│  - State diffs                       │
└───────────────────┬──────────────────┘
                    │
                    ▼
┌──────────────────────────────────────┐
│            Agent Layer               │
│        (LLM-based Interpreter)       │
│                                      │
│  - Reads component state             │
│  - Proposes actions or plans         │
│  - Asks clarifying questions         │
│  - NEVER executes actions            │
└───────────────────┬──────────────────┘
                    │
                    ▼
┌──────────────────────────────────────┐
│          Execution Engine            │   ← Authority Boundary
│                                      │
│  - Role enforcement                  │
│  - Budgets & rate limits             │
│  - Approval workflows                │
│  - Execution windows                 │
│  - Policy-as-code                    │
│  - Deterministic execution           │
│  - Audit logging                     │
└───────────────────┬──────────────────┘
                    │
                    ▼
┌──────────────────────────────────────┐
│         Action Handlers              │
│                                      │
│  - Pure state mutation               │
│  - No auth logic                     │
│  - No side effects beyond state      │
└───────────────────┬──────────────────┘
                    │
                    ▼
┌──────────────────────────────────────┐
│        Persistent State              │
│                                      │
│  - Component snapshots               │
│  - Execution log                     │
│  - Explicit memory                   │
│  - Audit trail                       │
└──────────────────────────────────────┘
```

**Key Property**:
The execution engine is the only component allowed to mutate state.
All clients — chat UI, API calls, webhooks, schedulers — must pass through it.
