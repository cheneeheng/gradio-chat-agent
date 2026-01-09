# FAQ

## What is the difference between Session Memory and Session Facts?

The Gradio Chat Agent distinguishes between these two concepts based on their scope, versioning, and how the agent interacts with them.

### 1. Session Memory (`sys.memory`)
*   **Definition:** A specific **Component** defined in the application state.
*   **Location:** Defined in `src/gradio_chat_agent/registry/system_actions.py` as `memory_component` with ID `sys.memory`.
*   **Scope:** **Project-Wide (Shared)**. Since it lives in the `StateSnapshot`, it is shared by all users interacting with that project state.
*   **Behavior:** It is **Transactional and Versioned**. Changes to memory are recorded as state transitions (snapshots) with diffs.
*   **Access:** Modified by the Agent via specific actions: `memory.remember` and `memory.forget`.

### 2. Session Facts (Repository Layer)
*   **Definition:** A **Persistence Utility** method exposed by the `StateRepository` interface.
*   **Location:** Defined in `src/gradio_chat_agent/persistence/repository.py` (methods `save_session_fact`, `get_session_facts`).
*   **Scope:** **User-Specific**. The storage key is generated using both `project_id` and `user_id`.
*   **Behavior:** It is a **Simple Key-Value Store** separate from the main state machine history. It is not versioned.
*   **Access:** Direct repository calls. This is typically used for user-specific preferences or long-term recall that doesn't need to be part of the shared project state.

### Summary Table

| Feature | Session Memory (`sys.memory`) | Session Facts (Repository) |
| :--- | :--- | :--- |
| **Type** | Application State Component | Persistence Layer Data |
| **Scope** | **Project** (Shared State) | **User** (Personalized) |
| **Versioning** | Yes (Snapshots & Diffs) | No (Current Value Only) |
| **Agent Access**| Via Actions (`remember`/`forget`) | Direct Repo Access |
| **Primary Use**| Active context for the conversation | Long-term user data / Preferences |
