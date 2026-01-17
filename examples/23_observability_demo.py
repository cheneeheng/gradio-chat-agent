"""Example of Structured JSONL Logging.

This example demonstrates:
1. Setting up the centralized logger.
2. Emitting logs with extra context fields.
3. How the output looks in JSONL format.
"""

from gradio_chat_agent.observability.logging import get_logger, setup_logging


def run_example():
    # 1. Initialize logging
    # You can set LOG_LEVEL=DEBUG environment variable to see more.
    setup_logging(level="DEBUG")

    logger = get_logger("example.observability")

    # 2. Simple info log
    logger.info("Application starting up...")

    # 3. Log with extra fields (The pattern used in ExecutionEngine)
    logger.info(
        "User performed an action",
        extra={
            "extra_fields": {
                "event": "user_action",
                "user_id": "alice_123",
                "action_id": "demo.counter.increment",
                "cost": 1.0,
            },
            "request_id": "req-abcd-efgh",
            "project_id": "proj-demo",
        },
    )

    # 4. Error log with exception
    try:
        1 / 0  # type: ignore
    except ZeroDivisionError:
        logger.exception(
            "An unexpected error occurred",
            extra={"project_id": "proj-demo", "request_id": "req-failed"},
        )

    print("\n--- Example Complete ---")
    print("Check the stdout above for JSONL formatted logs.")


if __name__ == "__main__":
    run_example()
