FROM python:3.12-slim

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

# Set working directory
WORKDIR /app

# Copy dependency files first for better caching
COPY pyproject.toml uv.lock ./

# Install dependencies using uv
# --frozen ensures we use exact versions from uv.lock
# --no-dev excludes development dependencies
RUN uv sync --frozen --no-dev

# Copy application source code
COPY src ./src
COPY README.md ./

# Create a non-root user for security
RUN useradd -m appuser && chown -R appuser /app
USER appuser

# Expose the Gradio port
EXPOSE 7860

# Environment variables
ENV GRADIO_SERVER_NAME="0.0.0.0"
ENV GRADIO_SERVER_PORT="7860"
ENV PYTHONPATH="/app/src"

# Run the application
CMD ["uv", "run", "python", "src/gradio_chat_agent/app.py"]
