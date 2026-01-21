# Pantry Component Extraction Report

This document outlines the consolidated architectural plan for extracting the "Pantry" suite of libraries. The components are grouped by **specific use case** rather than file type, ensuring each library solves a distinct problem.

## 1. Pantry Core (`pantry-core`)
**Usecase:** **The Kernel.** Managing application state, enforcing governance (permissions/budgets), and executing intents.
**Description:** The foundational library required by all other components. It defines the "Physics" of the agent world (State, Actions, Plans, Users).
**Source Files:**
*   `src/gradio_chat_agent/execution/engine.py`
*   `src/gradio_chat_agent/models/` (All models)
*   `src/gradio_chat_agent/registry/abstract.py`
*   `src/gradio_chat_agent/persistence/repository.py`
*   `src/gradio_chat_agent/persistence/in_memory.py` (Default implementations)
*   `src/gradio_chat_agent/registry/in_memory.py` (Default implementations)
*   `src/gradio_chat_agent/chat/adapter.py` (Base Interface)
*   `src/gradio_chat_agent/utils.py` (State Diff & Checksum logic)

## 2. Pantry Service (`pantry-service`)
**Usecase:** **The Application Controller.** Exposing core logic to the outside world (API/UI/CLI) in a consistent, transport-agnostic way.
**Description:** A service layer (`ApiEndpoints`) that wraps the Kernel. It handles request validation, role resolution, and response standardization (`ApiResponse`) so that the Web UI and REST API behave identically.
**Source Files:**
*   `src/gradio_chat_agent/api/endpoints.py`
*   `src/gradio_chat_agent/models/api.py`

## 3. Pantry UI (`pantry-ui`)
**Usecase:** **The Interface.** Building reactive, state-driven user interfaces with Gradio.
**Description:** A library bridging Pantry State to Gradio Components. It includes the `UIBinder` for reactive updates, the standard `AgentTheme` for styling, and the `UIController` layout logic.
**Source Files:**
*   `src/gradio_chat_agent/ui/binder.py`
*   `src/gradio_chat_agent/ui/layout.py`
*   `src/gradio_chat_agent/ui/theme.py`

## 4. Pantry Store (`pantry-store-sql`)
**Usecase:** **Persistence.** Saving state, history, and users to a production database.
**Description:** An SQLAlchemy-based adapter for the Repository interface. It handles database connections, schema migrations (models), and secure storage (encryption/hashing).
**Source Files:**
*   `src/gradio_chat_agent/persistence/sql_repository.py`
*   `src/gradio_chat_agent/persistence/models.py`
*   `src/gradio_chat_agent/utils.py` (SecretManager, hash_password)

## 5. Pantry Brain (`pantry-brain-openai`)
**Usecase:** **Intelligence.** Connecting the agent to Large Language Models.
**Description:** An adapter that translates the Pantry Action Registry into OpenAI Function Definitions and converts LLM responses into structured Pantry Intents.
**Source Files:**
*   `src/gradio_chat_agent/chat/openai_adapter.py`

## 6. Pantry Automation (`pantry-automation`)
**Usecase:** **Background Execution.** Running tasks asynchronously or on a schedule.
**Description:** A suite of execution strategies for "headless" operation:
*   **Scheduler:** Cron-based triggers (APScheduler).
*   **Queue:** Background task offloading (Huey).
*   **Reactor:** Event-driven side-effects (`AuditLogObserver`).
**Source Files:**
*   `src/gradio_chat_agent/execution/scheduler.py`
*   `src/gradio_chat_agent/execution/tasks.py`
*   `src/gradio_chat_agent/execution/observer.py`

## 7. Pantry Ops (`pantry-ops`)
**Usecase:** **Operations & Monitoring.** Keeping the agent healthy and within budget.
**Description:** A "Day 2" operations stack including structured JSON logging, Prometheus metrics, rule-based alerting, and budget forecasting intelligence.
**Source Files:**
*   `src/gradio_chat_agent/observability/logging.py`
*   `src/gradio_chat_agent/observability/metrics.py`
*   `src/gradio_chat_agent/observability/alerting.py`
*   `src/gradio_chat_agent/execution/forecasting.py`

## 8. Pantry Gatekeeper (`pantry-gatekeeper`)
**Usecase:** **Authentication.** Securing the agent's endpoints.
**Description:** A manager for OIDC (OpenID Connect) integration with FastAPI, handling session management, login flows, and Bearer token validation.
**Source Files:**
*   `src/gradio_chat_agent/auth/manager.py`

## 9. Pantry StdLib (`pantry-stdlib`)
**Usecase:** **Standard Toolkit.** "Batteries included" capabilities for new agents.
**Description:** A collection of standard Component and Action definitions that most agents need:
*   **Memory:** `sys.memory` (Remember/Forget).
*   **Controls:** Text Inputs, Sliders, Status Indicators.
*   **Inference:** Model Selector, Prompt Editor.
**Source Files:**
*   `src/gradio_chat_agent/registry/std_lib.py`
*   `src/gradio_chat_agent/registry/system_actions.py`
*   `src/gradio_chat_agent/registry/std_models.py`

## 10. Pantry Browser (`pantry-skill-browser`)
**Usecase:** **Web Interaction.** Giving the agent a web browser.
**Description:** A specialized skill package wrapping Playwright. It defines the `browser` component and the executors for navigation and interaction. Kept separate due to heavy dependencies.
**Source Files:**
*   `src/gradio_chat_agent/registry/web_automation.py`
*   `src/gradio_chat_agent/execution/browser_executor.py`

## 11. Pantry Admin (`pantry-admin`)
**Usecase:** **Administration.** Managing the system from the command line.
**Description:** A CLI tool for creating projects, managing users, rotating secrets, and validating policy files.
**Source Files:**
*   `src/gradio_chat_agent/cli.py`
*   `src/gradio_chat_agent/tools/load_policy.py`
