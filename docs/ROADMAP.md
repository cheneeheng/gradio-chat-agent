# Project Roadmap

This roadmap outlines the evolution of the governed execution control plane and its chat-based interface.

---

## 1. Core System (Completed)

- Deterministic execution engine
- Project-scoped state and roles
- Action registry + handlers
- Chat UI with plan previews
- Replay + audit logging
- Persistent memory
- Webhooks + scheduler
- Budgets, rate limits, quotas
- Approval workflows
- Execution windows
- Policy-as-code
- Forecasting + alerts
- Adaptive budgets
- Org-level rollups

The system is now architecturally complete.

---

## 2. Near-Term Enhancements

### 2.1 Identity & Access

- OIDC / OAuth login
- Group-based role assignment
- Org-level RBAC

### 2.2 Secrets Management

- Encrypted secret storage
- Scoped secret access for actions
- Secret rotation

### 2.3 Component Ecosystem

- Standard component library
- Component discovery
- Component versioning

### 2.4 Developer Experience

- CLI for managing projects, roles, and policies
- Component scaffolding tool
- Policy validation tool

---

## 3. Medium-Term Enhancements

### 3.1 Distributed Execution

- Worker pool
- Job queue
- Retry semantics
- Idempotency keys

### 3.2 Observability

- Prometheus metrics
- Grafana dashboards
- Structured logs

### 3.3 Safety & Governance

- Static policy verification
- Plan-level simulation
- Multi-step approval chains

---

## 4. Long-Term Vision

### 4.1 Multi-Agent Collaboration

- Multiple agents proposing plans
- Arbitration and consensus
- Agent specialization

### 4.2 Autonomous Mode (Governed)

- Fully autonomous execution within strict budgets
- Human override and kill-switch
- Predictive safety checks

### 4.3 Enterprise Deployment

- Multi-tenant isolation
- Horizontal scaling
- Policy federation across orgs

---

## Summary

The system is already a robust control plane with a chat interface.  
The roadmap focuses on:

- Hardening governance
- Improving developer experience
- Scaling execution
- Enhancing observability

This ensures the platform remains safe, extensible, and production-ready.
