#!/bin/bash

# Example of how to configure CORS allowed origins via env vars.

# 1. Set allowed origins (comma-separated)
export GRADIO_ALLOWED_ORIGINS="http://localhost:3000,https://my-frontend-app.com"

echo "Starting server with CORS allowed origins: $GRADIO_ALLOWED_ORIGINS"

# 2. Run the app
# uv run python src/gradio_chat_agent/app.py
echo "Command: GRADIO_ALLOWED_ORIGINS=$GRADIO_ALLOWED_ORIGINS uv run python src/gradio_chat_agent/app.py"
