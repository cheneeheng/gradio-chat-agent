# Execution Engine Architecture

## Overview

The **Execution Engine** is the authoritative heart of the `gradio-chat-agent`. It is responsible for accepting a structured `ChatIntent`, validating it against policies and registries, applying state mutations, and persisting the result.

It guarantees that **no state change happens off-the-record**. Every change is an atomic transaction that includes the mutation, the audit log, and the resource accounting.

---

## Core Responsibilities

1.  **Authorization & Governance**: Verifying that the user has the required roles and that the project has sufficient budget.
2.  **Validation**: Ensuring the requested action exists and the inputs match the schema.
3.  **Concurrency Control**: Serializing mutations within a project to ensure deterministic state transitions.
4.  **Atomic Execution**: Applying the handler, creating a snapshot, and writing the execution log in a single transaction (or logically atomic operation).

---

## Request Lifecycle

The engine processes an intent through the following pipeline:

### 1. Context Resolution
*   **Input**: `ChatIntent`, `ProjectIdentity`, `UserIdentity`.
*   **Action**: Load the current `StateSnapshot` for the project. If none exists, load the initial state.
*   **Check**: Verify if the project is archived or locked.

### 2. Authorization Gate
*   **Role Check**: Compare user roles (e.g., `viewer`, `operator`) against the `ActionDeclaration.permission.required_roles`.
*   **Confirmation Check**: If `confirmation_required` is True, verify that `intent.confirmed` is True.
*   **Risk Check**: If execution mode is `autonomous` and action risk is `high`, ensure explicit confirmation is present.

### 3. Validation
*   **Schema Validation**: Validate `intent.inputs` against `ActionDeclaration.input_schema` using `jsonschema`.
*   **Precondition Check**: Evaluate all `ActionPrecondition` expressions against the current state snapshot.
    *   *Implementation Note*: Preconditions use a safe subset of Python expression evaluation (AST parsing) to prevent code injection.

### 4. Governance & Limits
*   **Rate Limiting**: Check actions/minute and actions/hour counters.
*   **Budgeting**: Calculate the abstract cost of the action. Check if `daily_budget` would be exceeded.
*   **Approval**: Check if the action's cost or risk triggers a requirement for human approval (e.g., high cost actions by non-admin users).
    *   If approval is required, the engine returns a result with `status="pending_approval"`. The state is *not* mutated.
    *   The UI/Agent must then solicit approval (from an admin) and re-submit the intent (potentially via a different flow or user).

### 5. Execution (Mutation)
*   **Locking**: Acquire a project-level lock. This ensures that no two requests mutate the same project state simultaneously.
*   **Invocation**: Call the registered `ActionHandler` with `(inputs, current_state)`.
*   **Output**: The handler returns `(new_state, state_diff, message)`.
    *   *Constraint*: Handlers must be **pure**. They should not make external API calls or read DB state directly. They only transform the passed state dictionary.

### 6. Persistence & Commit
*   **Snapshot**: Create a new `StateSnapshot` with a unique ID.
*   **Log**: Create an `ExecutionResult` record containing the diff, status, and metadata.
*   **Atomic Write**: Save both the Snapshot and the ExecutionResult to the persistence layer.
*   **Unlock**: Release the project lock.

---

## Side Effects & Replayability

To maintain the **Auditability** and **Replayability** pillars, the engine enforces a strict separation between state mutation and real-world side effects:

1.  **State Mutation (The Handler)**: The pure function that updates the `components` dictionary. This is what is re-run during a "Replay".
2.  **Side Effects (The Dispatcher)**: Actions that interact with external systems (e.g., sending an email, moving a robot arm, calling a third-party API). 
    *   Side effects are triggered **after** a successful state commit.
    *   The engine provides a `post_execution` hook for side effects.
    *   **Crucially**: Side effects are **disabled** during a Replay or Simulation to prevent unintended real-world consequences.

---

## Error Handling

The engine distinguishes between:
*   **Rejections**: Policy failures (auth, budget, preconditions). State is unchanged. Logged as `status=rejected`.
*   **Failures**: Runtime errors inside the handler. State is unchanged (rolled back). Logged as `status=failed`.

---

## Interfaces

### Input
The engine accepts a `ChatIntent`:
```python
@dataclass
class ChatIntent:
    action_id: str
    inputs: dict
    confirmed: bool
    execution_mode: str
    ...
```

### Output
The engine returns an `ExecutionResult`:
```python
@dataclass
class ExecutionResult:
    status: Literal["success", "rejected", "failed"]
    state_diff: List[StateDiffEntry]
    state_snapshot_id: str
    error: Optional[ExecutionError]
    ...
```

---

## Plan Execution

When the engine receives an `ExecutionPlan` (via `api_execute_plan` or internal call), it processes the steps sequentially in a loop:

1.  **Initialization**: Validate the plan structure.
2.  **Step Loop**: For each `ChatIntent` in `plan.steps`:
    *   **Context Check**: Verify `max_steps` limit for the current execution mode.
    *   **Execute**: Call `execute_intent(intent)`.
    *   **Check Result**:
        *   If `status == "success"`, continue to next step.
        *   If `status == "rejected"` or `failed`, **ABORT** the plan immediately.
3.  **Result Aggregation**: Return the list of `ExecutionResult`s for all attempted steps.

**Atomicity**: Plans are **NOT** atomic transactions. If Step 3 fails, Steps 1 and 2 remain committed. This "partial success" model allows for easier debugging and resumption of long-running workflows.

---

## Simulation (Dry-Run) Mode

The engine supports a **Simulation** path used for plan previews and "what-if" analysis:

1.  **Virtual Execution**: The engine runs the `ActionHandler` against the current state.
2.  **No Commit**: The resulting `StateSnapshot` and `ExecutionResult` are **NOT** written to the database.
3.  **Side Effect Suppression**: The `post_execution` hooks are skipped.
4.  **Output**: Returns a result with `status="success"` but marked as `simulated=True`.

---

## State Reversal (Revert)

The **Revert** operation is a special authoritative action:

1.  **Lookup**: Load the `StateSnapshot` associated with the target `snapshot_id`.
2.  **Validation**: Ensure the snapshot belongs to the current project.
3.  **Branching**: Instead of deleting history, the engine creates a **new** `ExecutionResult` of type `revert`.
4.  **Commit**: The target snapshot is saved as the "Latest" state, effectively rolling back the project while preserving the audit trail of the reversal itself.
