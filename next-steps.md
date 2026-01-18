# Next Steps

## 1. Agent & Intelligence

- [x] **Interactive Safety Behavior:** Update the agent to detect precondition failures and automatically suggest the "minimal next action" required to satisfy the state (e.g., suggesting a "login" action if an "upload" action fails due to missing auth state).
- [x] **Structured Clarification Protocol:** Enforce a strict format for `ask_clarification` where multiple matching actions are presented as a numbered list with titles and IDs.
- [x] **Simulation (Dry-Run) Mode:** Implement a simulation path in the `ExecutionEngine` to allow agents to preview the state impact of a plan without committing changes or triggering side effects.
- [x] **Plan Step Limits:** Enforce `max_steps` per plan based on the execution mode (Interactive vs. Autonomous) to prevent runaway loops.
- [x] **Multi-step Planning:** Update `OpenAIAgentAdapter` to detect and process multiple tool calls, wrapping them into an `ExecutionPlan` instead of just the first `ChatIntent`.
- [x] **Optimized Parameter Completion:** Refine the clarification logic to ensure the agent asks _only_ for the specific missing required fields identified by the JSON Schema, minimizing user friction.
- [x] **Context Enrichment:** Inject recent execution results (history) and state diffs into the LLM system prompt to help the agent verify its own progress.
- [x] **Memory Store Alignment:** Refactor the `memory.remember` and `memory.forget` action handlers in `system_actions.py` to utilize the authoritative `session_facts` table in the repository instead of mutating the `sys.memory` UI component state.
- [x] **User-Scoped Context:** Update the `AgentAdapter` interface and `on_submit` logic to pass the `user_id`, ensuring that the "Memory Block" injection is strictly scoped to the specific (user, project) pair as required for privacy.
- [x] **Explicit Fact Injection:** Explicitly retrieve and inject session facts from the `SessionFact` repository into the context window.
- [x] **Multimodal Support:**
  - **UI Collection:** Update the Gradio `on_submit` handler to extract uploaded image data from the chat history and package it into the `media` field of the `ChatIntent`.
  - **Vision Interpretation:** Complete the `# TODO` in `OpenAIAgentAdapter` to convert `IntentMedia` into OpenAI-compatible `image_url` message parts.
  - **Media Hashing:** Update the `ExecutionEngine` to store a hash or reference of the intent media in the audit log metadata, satisfying the requirement to avoid full image persistence in the database.
- [x] **Automated Confirmation Detection:** Implement logic in the `AgentAdapter` or `OpenAIAgentAdapter` to recognize user approval keywords (e.g., "confirm", "proceed", "yes") and automatically re-submit the previous rejected intent with the `confirmed=true` flag, fulfilling the interaction pattern in the protocol.
- [x] **Hallucination Control Loop:** Implement an internal retry loop in the adapter to catch invalid `action_id` calls or schema violations.
- [x] **LLM Proxy & Azure Support:** Implement the `OPENAI_API_BASE` configuration in `OpenAIAgentAdapter` to allow integration with Azure OpenAI or local LLM gateways (e.g., LiteLLM, vLLM).

## 2. Session Memory & Facts

- [x] **Missing Fact Injection (Read Path):** Update the `on_submit` handler in `layout.py` and the `AgentAdapter` interface to fetch and inject session facts for the current `(user_id, project_id)` at the start of every chat turn.
- [x] **Memory Store Alignment:** Refactor the `memory.remember` and `memory.forget` action handlers in `system_actions.py` to utilize the authoritative `session_facts` table in the repository instead of mutating the `sys.memory` UI component state.
- [x] **User-Scoped Context:** Ensure that the "Memory Block" injection is strictly scoped to the specific (user, project) pair as required for privacy.
- [x] **Memory Management UI:** Implement a "Memory List" tab in the State Inspector (matching the `MemoryList` pattern in the reference snippets) to allow users to view, edit, and delete stored facts manually.

## 3. User Interface & Experience

- [x] **Team/Membership Management UI:** Implement a "Team" or "Settings" tab visible only to Admins, allowing for inviting users, updating roles (`viewer`, `operator`, `admin`), and removing members.
- [ ] **Rich UI Binding:** Implement a declarative mechanism to bind Gradio components (Sliders, Checkboxes, etc.) directly to paths in the `StateSnapshot`. Ensure UI updates are a pure function of the central state as required by the registry contract.
- [x] **Custom Theme:** Create `src/gradio_chat_agent/ui/theme.py` using Gradio's `Theme` class to establish a consistent brand identity (colors, fonts, spacing).
- [x] **CSS Styling:** Inject custom CSS into the `gr.Blocks` layout to refine the appearance of Chatbot bubbles, Plan Preview blocks, and state JSON viewers.
- [ ] **Session Token Management:** Update the UI state to include `session_token` handling for future authenticated OIDC requests.
- [x] **Raw Trace Inspectors:** Add specialized tabs in the State Inspector to display the raw JSON of the last `ChatIntent` and `ExecutionResult` for developer debugging.
- [x] **Visual Action Feedback:** Implement "Success/Failure" animations or status indicators directly on the components in the State Inspector.

## 4. Governance & Policy Enforcement

- [x] **Invariant Enforcement:** Update the `ExecutionEngine` to validate component `invariants` after every action execution, rolling back state if a constraint is violated.
- [x] **Action Visibility Filtering:** Implement logic in the `Registry` and `ApiEndpoints` to filter available actions based on the `visibility` field and user roles.
- [x] **Action Budgets:** Implement a per-action cost tracking system (`ActionBudgets`) to allow granular control over expensive operations.
- [x] **Budget Enforcement:** Implement action cost calculation and track/enforce `daily_budget` within the `ExecutionEngine`.
- [x] **Hourly Rate Limiting:** Extend the engine to enforce `per_hour` limits in addition to `per_minute`.
- [x] **Execution Windows:** Implement time-of-day and day-of-week restrictions in governance policies and validate them in the engine.
- [x] **Approval Workflows:** Implement a `pending_approval` status for actions that exceed cost thresholds or risk levels.
- [x] **Project Lifecycle Enforcement:** Add checks to the `ExecutionEngine` to block intents if a project is archived or locked.
- [ ] **Advanced Policy Engine:** Transition from simple JSON limit checks to a more robust policy engine (e.g., OPA/Rego or a custom DSL).
- [x] **Safer Preconditions:** Replace `eval()` in the `ExecutionEngine` with a restricted evaluator (e.g., `RestrictedPython` or an AST-based validator).
- [x] **Centralized Engine Configuration:** Implement an `EngineConfig` model in `engine.py` to manage runtime flags like `require_confirmed_for_confirmation_required`, decoupling core logic from environment-specific defaults as defined in the configuration docs.

## 5. Automation & Background Tasks

- [x] **Scheduler Worker:** Implement a background process (e.g., using `APScheduler` or a simple loop) to trigger actions defined in the `Schedule` model.
- [x] **Schedule Execution Identity:** Ensure scheduled tasks execute using a dedicated "System" user identity with appropriate permissions.
- [x] **Webhook Signature Verification:** Implement secure HMAC-SHA256 verification (e.g., `X-Hub-Signature`) for incoming webhooks using the registered secret.
- [x] **Jinja2 Webhook Templating:** Replace basic key substitution in `webhook_execute` with a full Jinja2 environment for mapping complex payloads to action inputs.
- [x] **Side Effect Dispatcher:**
  - [x] **Hook System:** Implement a `post_execution` hook in the `ExecutionEngine` to trigger external actions (e.g., API calls) only after state is successfully committed.
  - [x] **Replay Safety:** Implement a global `execution_context` or mode flag to ensure side effects are strictly suppressed during "Replay" or "Simulation" paths.
  - **Async Observers:** Design a background observer pattern that polls the audit log for successful mutations to trigger long-running or unreliable external tasks asynchronously.
- [ ] **Task Retries:** Add retry logic and error handling for failed scheduled tasks and webhook triggers.

## 6. Component Ecosystem

- [ ] **Versioning:** Update the Registry to support versioned components/actions (e.g., `demo.counter@v1`).
- [ ] **Standard Library Expansion:** Expand the `std` namespace with common components (`std.text_input`, `std.slider`, `std.status_indicator`) and layouts to provide a consistent base for all projects.
- [ ] **Web Automation Suite:** Implement a high-level browser component suite (`browser.click`, `browser.type`, `browser.scroll`) based on Playwright.
- [ ] **Standard Model/Inference Suite:** Implement the `model.selector` and `inference.run` examples from the documentation as a reusable package.

## 7. Developer Experience (CLI & API)

- [x] **Standardized API Responses:** Refactor `ApiEndpoints` to use a consistent response envelope (`{"code": 0, "message": "success", "data": {...}}`) as seen in the `APIResponse` snippets.
- [x] **API Simulation Endpoints:** Implement `api_simulate_intent` and `api_simulate_plan` in `endpoints.py`, wrapping the planned simulation logic in the `ExecutionEngine`.
- [x] **CLI Tool:** Create a `typer` or `click` based CLI (`gradio-agent`) that exposes the management API.
  - `gradio-agent project create`
  - `gradio-agent user create` (with password hashing)
  - `gradio-agent user password-reset`
  - `gradio-agent webhook list`
- [x] **Policy Validation:** Add a CLI command to validate policy YAML files against the schema before loading.

## 8. Observability & Analytics

- [x] **Structured Operational Logging:** Replace `print()` statements with a centralized Python `logging` setup that emits JSON-structured lines (JSONL) to `stdout` for production ingestion (Splunk/Datadog/Elastic).
- [x] **Environment-Driven Log Verbosity:** Integrate the `LOG_LEVEL` environment variable into the logging initialization to allow dynamic control over system verbosity without code changes.
- [x] **Log Traceability:** Ensure every application log entry includes the `component`, `event`, `request_id`, and `project_id` for easy correlation between operational logs and the authoritative Audit Log.
- [x] **Full Intent Logging:** Update the `Execution` model and `SQLStateRepository` to store the full intent object (including action inputs and metadata) for every attempt, as required by the protocol for auditability and replay.
- [x] **Execution Metadata:** Add `execution_time`, `cost`, and `user_id` attribution to the `Execution` model for detailed resource accounting.
- [x] **Prometheus Metrics Suite:** Implement a `/metrics` endpoint and instrument the application for the following indicators:
  - `engine_execution_total` (Counter with status/action labels)
  - `engine_execution_duration_seconds` (Histogram for latency)
  - `budget_consumption_total` (Counter for abstract cost)
  - `llm_token_usage_total` (Counter for model tokens)
  - `active_projects` (Gauge)
- [ ] **Forecasting Service:** Implement a background job to analyze historical execution data and predict project budget exhaustion.
- [ ] **Operational Alerting:** Create a system to trigger alerts (e.g., via system webhooks or Prometheus rules) for:
  - High Failure Rates (e.g., >5% failure rate over 5 minutes)
  - LLM Latency Quantiles (e.g., P95 duration > 10 seconds)
  - Budget exhaustion (80%/90%/100% thresholds)
- [ ] **Org-level Rollups:** Implement global management APIs to aggregate usage, costs, and audit logs across all projects.

## 9. Platform Management

- [ ] **Global User Registry:** Implement API endpoints for system administrators to provision and manage users globally, independent of project membership.
- [ ] **Authority Separation:** Implement platform-wide RBAC logic to distinguish between System Admins (global access) and Project Admins (scoped access).
- [ ] **Policy Templating:** Implement a "System Template" system to automatically apply default rate limits and budgets when a new project is created via `api_manage_project`.
- [ ] **Purge Confirmation Gate:** Add a required confirmation flag and high-risk validation logic to the `PURGE` operation in `ApiEndpoints` to prevent accidental global data loss.
- [ ] **Global Observability (Rollups):** Implement cross-project analytics (`api_org_rollup`) allowing System Admins to view aggregate usage, costs, and failure rates across the entire platform.

## 10. Secrets Management & Security

- [ ] **Encryption:** Implement encryption for sensitive data at rest (e.g., Webhook secrets) in the `SQLStateRepository`.
- [ ] **Secret Rotation:** Add API endpoints to rotate secrets for webhooks and other credentials.
- [ ] **Bearer Token Lifecycle:** Implement logic for Admins to generate, list, and revoke API Bearer Tokens, moving beyond the hardcoded "admin" role for headless access.
- [ ] **CORS Configuration:** Integrate `GRADIO_ALLOWED_ORIGINS` into the server launch logic to allow secure cross-origin automation as specified in the documentation.
- [ ] **State Integrity Verification:** Implement a checksum/hashing system for state snapshots to detect and alert on unauthorized modifications.

## 11. Identity & Access (OIDC)

- [ ] **OIDC Integration:** Replace the mock authentication with a real OIDC/OAuth2 provider integration (e.g., using `Authlib`).
- [x] **User Model:** Implement a formal `User` table in the `SQLStateRepository` to store credentials, profiles, and organization links.
- [x] **Default Admin Bootstrap:** Implement logic to create a default `admin/admin` account on startup, guarded by the `ALLOW_DEFAULT_ADMIN` environment variable.
- [x] **RBAC Role Enforcement:** Update the `ExecutionEngine` to strictly validate user roles against action risk: `viewer` (no execution), `operator` (low/medium risk only), `admin` (full access).
- [ ] **RBAC Mapping:** Implement a dynamic mapping system to resolve Gradio session users to specific project roles (viewer, operator, admin).
- [ ] **Session Management:** Secure the API endpoints with proper Bearer token validation linked to the OIDC provider.

## 12. Deployment & Infrastructure

- [ ] **Production Dockerfile:** Create a root `Dockerfile` using `uv` and multi-stage builds, following the structure in the deployment guide.
- [x] **Health Check Endpoint:** Implement a dedicated FastAPI-based health endpoint (e.g., `/health`) to verify database and engine readiness.
- [ ] **Alembic Migrations:** Set up Alembic to manage database schema changes instead of relying on `metadata.create_all`.
- [ ] **Gunicorn/Uvicorn Wrapper:** Update the entry point to support production-grade ASGI servers with multiple worker processes.

## 13. Infrastructure & Scaling

- [ ] **Transactional Atomicity:** Update the `ExecutionEngine` and `SQLStateRepository` to ensure that the creation of a new `StateSnapshot` and the recording of the `ExecutionResult` occur within a single database transaction.
- [ ] **State Reconstruction (Time Travel):** Implement logic to reconstruct the application state at any point in time by replaying `ExecutionResult` diffs from an initial snapshot.
- [ ] **Differential Snapshots:** Optimize storage by implementing differential snapshots (storing only deltas) with periodic full-state "checkpoints."
- [ ] **Worker Pool & Job Queue:** Transition automated tasks (Schedules and Webhooks) to a dedicated background worker pool (e.g., using Redis and a job queue).
- [ ] **Distributed Locking:** Replace the local `threading.Lock` in `ExecutionEngine` with a distributed lock (e.g., via Redis or Database) to support multi-instance deployments.
- [x] **Environment-Aware Server Initialization:** Update `app.py` to respect `GRADIO_SERVER_NAME` and `GRADIO_SERVER_PORT` environment variables, enabling flexible deployment in containerized environments (Docker/K8s).
