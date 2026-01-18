#!/bin/bash

# Example of how to start the server with custom name and port via env vars.

# 1. Set custom host and port
export GRADIO_SERVER_NAME="127.0.0.1"
export GRADIO_SERVER_PORT="8080"

echo "Starting server on $GRADIO_SERVER_NAME:$GRADIO_SERVER_PORT..."

# 2. Run the app
# uv run python src/gradio_chat_agent/app.py
echo "Command: GRADIO_SERVER_NAME=$GRADIO_SERVER_NAME GRADIO_SERVER_PORT=$GRADIO_SERVER_PORT uv run python src/gradio_chat_agent/app.py"
