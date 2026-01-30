#!/bin/bash

# Example script to build and run the Gradio Chat Agent using Docker

# 1. Build the image
docker build -t gradio-chat-agent .

# 2. Run the container
# Note: You must provide your OPENAI_API_KEY
docker run -p 7860:7860 \
  -e OPENAI_API_KEY="your_api_key_here" \
  gradio-chat-agent
