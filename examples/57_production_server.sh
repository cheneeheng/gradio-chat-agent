#!/bin/bash

# Example of how to run the application using a production ASGI server (Gunicorn)
# with multiple worker processes.

# 1. Install gunicorn if not already present
# uv add gunicorn

# 2. Run using Gunicorn with Uvicorn workers
# -w 4: Use 4 worker processes
# -k uvicorn.workers.UvicornWorker: Use Uvicorn worker class
# --bind 0.0.0.0:7860: Bind to port 7860
# 'gradio_chat_agent.app:create_app()': Call the factory function

echo "Starting production server with Gunicorn..."
echo "Command: uv run gunicorn -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:7860 'gradio_chat_agent.app:create_app()'"

# Note: The scheduler will start in each worker process unless configured otherwise.
# For truly production-grade distributed tasks, consider Task 5.2 (Worker Pool & Job Queue).
