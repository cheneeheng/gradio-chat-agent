# Project Roadmap

This roadmap outlines the evolution of the governed execution control plane and its chat-based interface.

---

## 1. Core System (Completed)

- Deterministic execution engine
- Project-scoped state and roles (Basic RBAC)
- Action registry + handlers
- Chat UI with plan previews
- Replay + audit logging
- Persistent session memory
- Webhooks + scheduler (Management API)
- Rate limiting (RPM/RPH)
- Approval workflows (Single-step confirmation)
- Policy-as-code (YAML loading)

The core architecture is stable and functional for assisted execution.

---

## 2. Near-Term Enhancements

### 2.1 Identity & Access
- OIDC / OAuth login integration
- Group-based role assignment
- Org-level RBAC

### 2.2 Governance & Security
- **Execution windows** (time-boxed permissions)
- **Daily budget enforcement** in the execution engine
- Encrypted secret storage for webhooks
- Restricted execution environment (replace `eval()` for preconditions)

### 2.3 Automation & Worker
- Background scheduler worker (APScheduler/Worker process)
- Webhook trigger reliability (Retries + Idempotency)

### 2.4 Developer Experience
- CLI for managing projects, roles, and policies
- Policy validation tool (schema-based)
- Component scaffolding tool

---

## 3. Medium-Term Enhancements

### 3.1 Distributed Execution
- Worker pool
- Job queue
- Distributed locking improvements

### 3.2 Observability & Intelligence
- **Forecasting + alerts** for budget exhaustion
- **Adaptive budgets** based on historical usage
- Prometheus metrics + Grafana dashboards

### 3.3 Advanced Governance
- Static policy verification
- Plan-level simulation
- Multi-step approval chains (Org-level)

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
- **Org-level rollups** and global observability
- Policy federation across orgs
- Horizontal scaling

---

## Summary

The system is already a robust control plane with a chat interface.  
The roadmap focuses on:

- Hardening governance
- Improving developer experience
- Scaling execution
- Enhancing observability

This ensures the platform remains safe, extensible, and production-ready.
