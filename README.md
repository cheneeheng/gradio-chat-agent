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
  - Budgets, rate limits, approvals, and execution windows prevent runaway behavior

---

## What This Is (and Is Not)

### This is:

- A control plane for component‑based applications
- A safe way to let chat interfaces manipulate real state
- A foundation for automation with human oversight

### This is not:

- A chatbot that directly mutates state
- A prompt‑driven workflow engine
- A UI‑only demo

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

### Key Insight

The **execution engine** is the single source of truth.

Everything else — chat UI, API calls, webhooks, schedulers — is just a client.

---

## Components

### 1. Chat UI

- Built with Gradio
- Displays state, diffs, plans, and warnings
- Allows plan approval / rejection
- Never executes actions directly

### 2. Agent Layer

- Uses an LLM to interpret user intent
- Proposes actions or multi‑step plans
- Reads state and memory
- Cannot bypass engine rules

### 3. Execution Engine

Enforces:

- User × project roles (`viewer`, `operator`, `admin`)
- Project archival state
- Execution windows (time‑boxed permissions)
- Rate limits and quotas
- Project‑level and action‑level budgets
- Risk‑weighted execution costs
- Human approval workflows
- Replayability and audit logging

### 4. Persistence

- Snapshots of component state
- Execution logs with diffs
- Explicit session memory
- Project configuration and limits

### 5. Observability

- JSONL audit logs
- Metrics
- Budget usage tracking
- Forecasting and alerts

---

## Projects and Roles

- All state is scoped to **(user, project)**
- Users may have different roles per project
- Roles:
  - `viewer`: read‑only
  - `operator`: execute low/medium‑risk actions
  - `admin`: full control, role management, ownership transfer

---

## Governance Features

- **Budgets**
  - Project‑level
  - Per‑action
  - Risk‑weighted costs
- **Rate limits**
  - Per minute / hour / day
- **Approvals**
  - Cost‑based escalation
  - Role‑aware
- **Execution windows**
  - Time‑boxed permissions
- **Forecasting**
  - Predict budget exhaustion
- **Alerts**
  - Webhook notifications on thresholds
- **Adaptive limits**
  - Optional self‑tuning within bounds
- **Policy‑as‑code**
  - YAML‑defined governance rules

---

## Replay and Audit

Every execution:

- Is logged with inputs, outputs, diffs, and metadata
- Can be replayed deterministically
- Can be exported as JSON
- Is safe to inspect without side effects

---

## API Access

Gradio exposes all execution and audit endpoints as authenticated HTTP APIs.

This allows:

- Headless automation
- CI integration
- External tooling
- Webhooks and schedulers

All API calls go through the same execution engine.

---

## Why This Exists

Most “chat‑controls‑UI” demos fail because:

- The chat is the authority
- State changes are implicit
- There is no replay or audit
- Safety is handled in prompts

This project exists to show how to do it **correctly**.

---

## Status

This system is **architecturally complete**.

What remains is integration work:

- Identity federation (OIDC)
- Secrets management
- Distributed execution
- UI polish

None of these require changes to the core engine.

---

## Documentation

### Fundamentals
- [Core Concepts](docs/01_CORE_CONCEPTS.md)
- [Getting Started](docs/02_GETTING_STARTED.md)
- [Project Roadmap](docs/03_ROADMAP.md)

### System Architecture
- [Architecture Overview](docs/04_ARCHITECTURE.md)
- [Execution Engine](docs/05_EXECUTION_ENGINE.md)
- [Agent Layer](docs/06_AGENT_LAYER.md)
- [Persistence Layer](docs/07_PERSISTENCE_LAYER.md)
- [UI Architecture](docs/08_UI_ARCHITECTURE.md)

### Contracts & Registries
- [Chat Agent Contract](docs/09_CHAT_AGENT_CONTRACT.md)
- [Chat Control Protocol](docs/10_CHAT_CONTROL_PROTOCOL.md)
- [UI Component Registry](docs/11_UI_COMPONENT_REGISTRY.md)
- [UI Action Registry](docs/12_UI_ACTION_REGISTRY.md)

### Advanced Features
- [Automation System](docs/13_AUTOMATION_SYSTEM.md)
- [Session Memory (Facts)](docs/14_SESSION_MEMORY.md)
- [Multimodal Intent (Images)](docs/15_MULTIMODAL_INTENT.md)
- [Real-World Integration (Side Effects)](docs/16_SIDE_EFFECTS_GUIDE.md)

### Governance & Security
- [User & Role Management](docs/17_USER_MANAGEMENT.md)
- [Platform Governance](docs/18_PLATFORM_GOVERNANCE.md)
- [Threat Model](docs/19_THREAT_MODEL.md)
- [Observability Guide](docs/20_OBSERVABILITY.md)

### Development & Operations
- [Development Guide](docs/21_DEVELOPMENT_GUIDE.md)
- [API Reference](docs/22_API_REFERENCE.md)
- [Configuration Reference](docs/23_CONFIGURATION.md)
- [Deployment Guide](docs/24_DEPLOYMENT_GUIDE.md)
- [Troubleshooting Guide](docs/25_TROUBLESHOOTING.md)

### Appendix
- [Architecture Brainstorming](docs/99_ARCHITECTURE_BRAINSTORMING.md)

## License

MIT (or your choice)