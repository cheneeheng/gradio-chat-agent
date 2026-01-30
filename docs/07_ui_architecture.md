# UI Architecture (Gradio)

## Overview

The user interface is built entirely using **Gradio**. It is designed to be a "Thin Client" that renders the state of the backend Execution Engine. The UI does not hold authoritative state; it mirrors the `StateSnapshot` and `ExecutionResult`s from the database.

---

## Layout Structure

The application layout is defined in `src/gradio_chat_agent/app.py` (or `ui/layout.py`). It typically consists of:

1.  **Sidebar / Control Panel**:
    *   **Project Selector**: Dropdown to switch between projects.
    *   **Mode Selector**: Toggle between `interactive`, `assisted`, and `autonomous`.
    *   **User Info**: Display current user identity and role.

2.  **Main Chat Area**:
    *   **Chatbot Component**: Renders the conversation history.
    *   **Input Box**: For user commands.
    *   **Plan Preview**: A dynamic area that appears when the agent proposes a multi-step plan (`ProposeExecutionPlan`). It contains "Approve" and "Reject" buttons.

3.  **State Inspector (Right Panel)**:
    *   **Live State**: JSON view or specialized rendering of the current component state (e.g., the Counter value).
    *   **State Diffs**: Visual feedback of what changed in the last action.
    *   **Debug/Trace**: Optional tabs for showing raw Intent/Result JSONs for developers.

---

## Event Handling

Gradio relies on event listeners (`btn.click(...)`). In this architecture, event handlers are lightweight wrappers around the `ExecutionEngine`.

### 1. Message Submission
*   **Trigger**: User types in `ChatInput` and hits Enter.
*   **Flow**:
    1.  UI calls `agent.message_to_intent(...)`.
    2.  Agent returns a `ChatIntent`.
    3.  UI calls `engine.execute_intent(intent)`.
    4.  Engine returns `ExecutionResult`.
    5.  UI updates `Chatbot` with the result message and `StateInspector` with the new state.

### 2. Plan Approval
*   **Trigger**: Agent returns a `ProposeExecutionPlan` tool call.
*   **UI Behavior**:
    *   Instead of executing immediately, the UI renders the plan steps in a `gr.Markdown` block.
    *   Unlocks the "Approve" button.
*   **On Approval**:
    *   UI sends the *entire* plan back to the engine's `execute_plan` endpoint.

---

## State Management in Gradio

Gradio apps can be stateful per session. We use `gr.State` components to hold:
*   `current_project_id`: The ID of the active project context.
*   `session_token`: Authentication token (if not using basic auth).
*   `pending_plan`: The plan object waiting for approval.

**Crucially**, we do **not** store the application domain state (e.g., "counter value") in `gr.State`. We re-fetch it from the `ExecutionEngine`/DB on every interaction to ensure consistency.

## Styling & Customization

*   **Theme**: The app uses a custom Gradio theme defined in `src/gradio_chat_agent/ui/theme.py`.
*   **CSS**: Custom CSS is injected for finer control over the Chatbot bubble styling and Plan Preview layout.
