# Gradio Chat Agent — Governed Component Control via Chat

## Overview

This project implements a **governed execution control plane** for interactive applications, with a **chat‑based UI** as one of its clients.

Users interact with the system through a chat interface (powered by an LLM), which can **propose actions and plans** to manipulate application components. All execution is mediated by a deterministic engine that enforces **authorization, budgeting, rate limits, approvals, and auditability**.

The chat interface is **not authoritative**. It is a convenience layer on top of a strict execution engine.

---

## Core Principles

- **Separation of concerns**
  - The agent proposes
  - The engine decides
  - Handlers mutate state
- **No implicit authority**
  - UI, agent, API, webhooks, and schedulers all go through the same engine
- **Deterministic execution**
  - Every state change is logged, replayable, and auditable
- **Governed autonomy**
  - Budgets and rate limits prevent runaway behavior

---

## Architecture

```
Chat UI (Gradio)
        ↓
Agent (LLM proposes intents)
        ↓
Execution Engine (authority)
        ↓
Action Handlers (pure state mutation)
        ↓
Persistent State + Audit Log
```

---

## Key Components

1.  **Chat UI**: A "Thin Client" built with Gradio that renders state and submits intents.
2.  **Agent Layer**: An LLM-based interpreter that converts natural language to structured `ChatIntent`.
3.  **Execution Engine**: The authoritative heart that validates permissions, limits, and applies mutations.
4.  **Persistence**: SQL-backed storage for snapshots, audit logs, and session memory.
5.  **Observability**: Integrated Prometheus metrics, JSONL logging, and automated alerting.

---

## Documentation

For a comprehensive guide to the system, please refer to the **[Guide Book](docs/GUIDEBOOK.md)**.

### Quick Links
- **Fundamentals**: [Core Concepts](docs/01_core_concepts.md) | [Getting Started](docs/02_getting_started.md)
- **Architecture**: [System Overview](docs/03_architecture_overview.md) | [Execution Engine](docs/04_execution_engine.md)
- **Development**: [Development Guide](docs/20_development_guide.md) | [API Reference](docs/23_api_reference.md)
- **Operations**: [Deployment Guide](docs/21_deployment_guide.md) | [Observability](docs/19_observability.md)
- **Strategy**: [Product Roadmap](docs/25_product_roadmap.md)

---

## Why This Exists

Most “chat‑controls‑UI” demos fail because the chat is the authority, state changes are implicit, and safety is handled purely in prompts. This project demonstrates how to build a production-grade system where chat acts as a **governor**, not the driver.

---

## Status

The core architecture is complete and production-hardened. Current focus is on expanding the ecosystem of components and enhancing multi-tenant governance.

## License

MIT
