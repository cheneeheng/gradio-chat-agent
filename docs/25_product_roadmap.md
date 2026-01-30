# Product Roadmap: Scaling to Production

This document outlines the strategic roadmap for transforming `gradio-chat-agent` from a reference architecture into a solid, enterprise-ready product.

## 1. Infrastructure & Scalability

### Migration-Based Schema Management
- **Current State:** The system uses SQLAlchemy's `create_all`, which is unsuitable for production schema evolution.
- **Task:** Enforce **Alembic** for all schema changes. Disable auto-creation in production. Add CI/CD steps to validate migration paths.

### Robust Distributed Locking
- **Current State:** Locking relies on a SQL table or local `threading.Lock`.
- **Task:** Implement a **Redis-based** distributed lock (e.g., Redlock) to ensure high-performance, multi-replica safety in Kubernetes deployments.

### Persistent Task Queue Decoupling
- **Current State:** Side effects often run in-process or via simple polling.
- **Task:** Make a persistent job queue (Redis/Celery or cloud-native SQS/PubSub) a hard requirement for all side effects to ensure the API server remains responsive under load.

## 2. Security & Compliance

### Enterprise Secret Management
- **Current State:** Secrets are encrypted in the DB using an environment variable key.
- **Task:** Integrate with **HashiCorp Vault, AWS Secrets Manager, or Google Secret Manager**. Secrets should be fetched at runtime or injected via CSI drivers.

### Audit Log Immutability
- **Current State:** Execution records are standard mutable SQL rows.
- **Task:** Implement **WORM (Write Once, Read Many)** storage for audit logs. Ship logs to an immutable bucket (S3 Object Lock) or a dedicated logging service (Datadog/Splunk) before acknowledging transactions.

### Granular RBAC (Policy-as-Code)
- **Current State:** Fixed `viewer`, `operator`, and `admin` roles.
- **Task:** Integrate a dedicated policy engine like **OPA (Open Policy Agent)**. The Execution Engine should query OPA for every action, allowing dynamic, customer-defined permission policies.

## 3. User Experience & Architecture

### Headless API-First Design
- **Current State:** Logic is tightly coupled to the Gradio application.
- **Task:** Formalize the **FastAPI REST/GraphQL** layer as the primary product surface. Treat the Gradio app as just one consumer (the "Admin Console") of the authoritative API.

### Multi-Tenancy & Org Management
- **Current State:** Project-based, but lacks cross-customer isolation.
- **Task:** Introduce an `Organization` model above `Project`. Enforce strict tenant isolation using **Row Level Security (RLS)** in Postgres to prevent data leaks.

## 4. Intelligence & Reliability

### Model Agnosticism (LiteLLM)
- **Current State:** hardcoded `OpenAIAgentAdapter`.
- **Task:** Refactor the adapter to use **LiteLLM** or a similar abstraction to support 100+ models (Anthropic, Gemini, Llama 3) via simple configuration.

### Agent Evaluation Framework (Evals)
- **Current State:** No automated way to measure reasoning quality.
- **Task:** Build a CI/CD pipeline for **Agent Evals**. Create a suite of "Golden Scenarios" (input -> expected plan) to verify reasoning performance on every pull request.

## 5. Extensibility & Ecosystem

### Plugin Architecture
- **Current State:** Registry is populated via internal imports.
- **Task:** Implement a **Plugin System** using Python `entry_points`. Allow users to install 3rd-party packages that register their own Components and Actions automatically on startup.

### Outbound Webhooks
- **Current State:** Only inbound webhooks are supported.
- **Task:** Implement **Outbound Webhooks**. Allow external systems to subscribe to state change events (e.g., "Notify Slack when project budget reaches 90%").
