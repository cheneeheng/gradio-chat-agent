# Deployment Guide

This document outlines the strategies and best practices for deploying `gradio-chat-agent` into a production environment.

## Deployment Architecture

The application is designed to run as a stateless containerized service, backed by a persistent relational database.

```
[Load Balancer / Reverse Proxy (Nginx/Traefik)] (HTTPS)
       |
       v
[ Application Container (Gradio + Uvicorn) ]
       |
       +--- [ Persistent Database (PostgreSQL) ]
       |
       +--- [ LLM Provider API (OpenAI/Azure) ]
```

## Containerization

We recommend using Docker. Since this project uses `uv`, the Dockerfile should leverage it for fast, reliable builds.

### Recommended Dockerfile Structure

```dockerfile
FROM python:3.12-slim

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

WORKDIR /app

# Copy dependency files first
COPY pyproject.toml uv.lock ./

# Install dependencies using uv
# --frozen ensures we use exact versions from uv.lock
# --no-dev excludes development dependencies
RUN uv sync --frozen --no-dev

# Copy application source code
COPY src ./src

# Create a non-root user for security
RUN useradd -m appuser && chown -R appuser /app
USER appuser

# Expose the Gradio port
EXPOSE 7860

# Run the application
# Note: In production, Gradio runs its own server, but for high concurrency,
# you might wrap the underlying FastAPI app with Gunicorn/Uvicorn workers.
# For standard Gradio deployment:
CMD ["uv", "run", "python", "src/gradio_chat_agent/app.py"]
```

## Database Setup

While SQLite is the default for local development, **PostgreSQL** is strongly recommended for production to ensure:
1.  **Concurrency**: Better handling of locking and concurrent requests.
2.  **Reliability**: Durability guarantees for the Audit Log.
3.  **Scalability**: Handling large execution histories.

### Migration Strategy
On startup, the application currently initializes tables if they don't exist (`repo.create_tables`). For a mature production setup, integration with a migration tool like **Alembic** is recommended to handle schema changes over time.

**Current Behavior:** The app attempts to auto-create tables on launch. Ensure the database user has `CREATE TABLE` permissions or that tables are pre-provisioned.

## Security Considerations

### 1. HTTPS / TLS
Gradio can generate a public link, but for production, you should **disable** this and serve the app behind a reverse proxy (like Nginx, AWS ALB, or Cloudflare) that handles SSL termination.

### 2. Authentication
The built-in auth system uses a local database table (`users`).
*   **Initial Setup**: The app creates a default `admin` user if missing. **Immediately** change this password or use the API/CLI to create a real admin account and delete the default one.
*   **Session Security**: Ensure `GRADIO_SECRET_KEY` (if applicable) or session cookies are secure.

### 3. Secrets Management
Never commit `.env` files. Use your orchestration platform's secret management (K8s Secrets, AWS Secrets Manager) to inject environment variables.

## Health Checks

The application exposes Gradio endpoints. A basic health check can verify that the TCP port `7860` is accepting connections.

## Scaling

*   **Statelessness**: The application logic is stateless; all state is in the DB. You can run multiple replicas behind a load balancer.
*   **Locking**: The Execution Engine uses database-level or application-level locking (implemented via `threading.Lock` in the current in-memory reference).
    *   *Critical Note*: The current reference implementation uses in-memory locks (`threading.Lock`). **For multi-replica deployment, you must implement a distributed lock** (e.g., Redis-based or Postgres Advisory Locks) in the `StateRepository` to ensure strict serialization of actions per project.

## Backup & Disaster Recovery

The authoritative state of the system lives in the database. A production-grade deployment must ensure:

1.  **DB Backups**: Daily automated backups of the PostgreSQL/SQLite database.
2.  **Audit Log Archival**: Since the `executions` table grows indefinitely, implement a job to export and archive old records (e.g., > 90 days) to cold storage (S3/GCS) in JSONL format.
3.  **Point-in-Time Recovery**: PostgreSQL's PITR is recommended for high-stakes environments to recover state exactly as it was before a critical failure.
