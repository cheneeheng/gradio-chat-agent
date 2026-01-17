import json
import logging
import io
import pytest
from gradio_chat_agent.observability.logging import JsonFormatter, setup_logging, get_logger

def test_json_formatter():
    formatter = JsonFormatter()
    log_record = logging.LogRecord(
        name="test_logger",
        level=logging.INFO,
        pathname="test.py",
        lineno=10,
        msg="test message",
        args=(),
        exc_info=None
    )
    # Add extra fields as we do in the code
    log_record.extra_fields = {"event": "test_event", "custom": "value"}
    log_record.request_id = "req-123"
    log_record.project_id = "proj-1"
    
    formatted = formatter.format(log_record)
    data = json.loads(formatted)
    
    assert data["message"] == "test message"
    assert data["level"] == "INFO"
    assert data["component"] == "test_logger"
    assert data["event"] == "test_event"
    assert data["custom"] == "value"
    assert data["request_id"] == "req-123"
    assert data["project_id"] == "proj-1"
    assert "timestamp" in data

def test_setup_logging():
    # Use a string buffer to capture output
    log_output = io.StringIO()
    handler = logging.StreamHandler(log_output)
    handler.setFormatter(JsonFormatter())
    
    logger = logging.getLogger("test_setup")
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    
    logger.info("setup test", extra={"extra_fields": {"test": "ok"}})
    
    output = log_output.getvalue()
    data = json.loads(output)
    assert data["message"] == "setup test"
    assert data["test"] == "ok"

def test_get_logger():
    logger = get_logger("my_name")
    assert logger.name == "my_name"
    assert isinstance(logger, logging.Logger)
