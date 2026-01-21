# Development Guide

This guide covers how to set up your development environment, run tests, and adhere to project standards.

## Project Structure

```text
/workspace/
├── src/
│   └── gradio_chat_agent/    # Main application package
│       ├── chat/             # Chat agent logic and adapters
│       ├── execution/        # The deterministic execution engine
│       ├── models/           # Pydantic models (Actions, Components, Intents)
│       ├── observability/    # Logging and metrics
│       ├── persistence/      # Database and state repositories
│       ├── registry/         # Component and Action registries
│       ├── ui/               # Gradio UI layout and visualization
│       └── app.py            # Entry point
├── tests/                    # Pytest suite
├── docs/                     # Documentation and schemas
├── pyproject.toml            # Dependencies and tool config
├── README.md                 # Project overview
└── uv.lock                   # Lockfile
```

## Environment Setup

This project uses `uv` for dependency management.

1.  **Install uv** (if not already installed):
    ```bash
    curl -LsSf https://astral.sh/uv/install.sh | sh
    ```

2.  **Sync dependencies**:
    ```bash
    uv sync
    ```
    This creates a virtual environment in `.venv` and installs all required packages (including dev dependencies).

## Running the Application

To run the Gradio app locally with hot-reloading (if configured) or standard execution:

```bash
uv run python src/gradio_chat_agent/app.py
```

## Testing

We use `pytest` for testing.

-   **Run all tests**:
    ```bash
    uv run pytest
    ```

-   **Run with coverage**:
    ```bash
    uv run pytest --cov=src
    ```

## Linting and Formatting

We use `ruff` for both linting and formatting.

-   **Check for linting errors**:
    ```bash
    uv run ruff check .
    ```

-   **Fix linting errors (where possible)**:
    ```bash
    uv run ruff check --fix .
    ```

-   **Format code**:
    ```bash
    uv run ruff format .
    ```

## Adding New Actions/Components

1.  **Define the Model**: Add or update Pydantic models in `src/gradio_chat_agent/models/` if necessary.
2.  **Update Registry**:
    -   For **Components**: Update `src/gradio_chat_agent/registry/in_memory.py` (or the relevant registry file).
    -   For **Actions**: Update `src/gradio_chat_agent/registry/in_memory.py`. Ensure you define the `input_schema`, `preconditions`, and `effects`.
3.  **Implement Handler**: Add the logic in `src/gradio_chat_agent/registry/in_memory.py` (or a dedicated handler file).

    **Handler Signature:**
    ```python
    from typing import Any
    from gradio_chat_agent.models.state_snapshot import StateSnapshot
    from gradio_chat_agent.models.execution_result import StateDiffEntry

    def my_action_handler(
        inputs: dict[str, Any],
        snapshot: StateSnapshot
    ) -> tuple[dict[str, dict[str, Any]], list[StateDiffEntry], str]:
        """
        Args:
            inputs: Validated inputs from the intent.
            snapshot: Read-only current state.

        Returns:
            new_components: The complete new state dictionary for all components.
            diff: A list of StateDiffEntry objects describing the changes.
            message: A human-readable summary of what happened.
        """
        # ... logic ...
    ```

4.  **Update Docs**: If this is a public capability, update `docs/11_UI_COMPONENT_REGISTRY.md` or `docs/12_UI_ACTION_REGISTRY.md`.

## Testing Strategies

### Testing Handlers
Handlers are pure functions. Test them by passing a mock `StateSnapshot` and asserting the returned `new_components` and `diff`.

```python
def test_my_handler():
    inputs = {"value": 10}
    snapshot = StateSnapshot(..., components={"my.comp": {"val": 0}})
    new_state, diff, msg = my_action_handler(inputs, snapshot)
    assert new_state["my.comp"]["val"] == 10
```

### Testing the Engine
Use the `ExecutionEngine` with an in-memory registry to verify that permissions, limits, and preconditions are enforced before your handler is called.
