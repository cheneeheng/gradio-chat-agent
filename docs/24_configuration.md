# Configuration Reference

This document describes the environment variables and configuration options available for `gradio-chat-agent`.

## Environment Variables

The application relies on environment variables for sensitive credentials and infrastructure configuration.

### Core
| Variable | Description | Required | Default |
| :--- | :--- | :---: | :--- |
| `DATABASE_URL` | Connection string for the persistence layer. Supports SQLite and PostgreSQL. | No | `sqlite:///./gradio_chat_agent.sqlite3` |
| `LOG_LEVEL` | Python logging level (DEBUG, INFO, WARNING, ERROR). | No | `INFO` |

### LLM Provider
| Variable | Description | Required | Default |
| :--- | :--- | :---: | :--- |
| `LLM_PROVIDER` | The LLM backend to use. Options: `openai`, `gemini` (or `google`). | No | `openai` |
| `OPENAI_API_KEY` | API Key for OpenAI (or compatible provider). | Required if provider is `openai` | - |
| `OPENAI_MODEL` | Model identifier to use for the agent. | No | `gpt-4o-mini` |
| `OPENAI_API_BASE` | Base URL for the API (if using Azure or a local proxy). | No | `https://api.openai.com/v1` |
| `GOOGLE_API_KEY` | API Key for Google Gemini. | Required if provider is `gemini` | - |
| `GEMINI_MODEL` | Model identifier for Google Gemini. | No | `gemini-2.0-flash` |

### Gradio / Server
| Variable | Description | Required | Default |
| :--- | :--- | :---: | :--- |
| `GRADIO_SERVER_NAME` | Hostname to listen on. Set to `0.0.0.0` for Docker. | No | `127.0.0.1` |
| `GRADIO_SERVER_PORT` | Port to listen on. | No | `7860` |
| `GRADIO_AUTH_USERNAME` | *Deprecated*. Use database-backed auth instead. | No | - |

## Application Configuration

Beyond environment variables, certain behaviors are configured via code or database entries.

### Engine Configuration
Currently defined in `src/gradio_chat_agent/execution/engine.py` via `EngineConfig`.

*   `require_confirmed_for_confirmation_required`: (bool) Enforces strict confirmation checks. Default: `True`.

### Policies
Project-specific policies (Limits, Budgets, Approvals) are stored in the database but can be initialized from YAML files.

See `docs/policies/example-project.yaml` for the structure.

## Database Connection Strings

**SQLite** (Local Dev):
```bash
DATABASE_URL=sqlite:///./local.db
```

**PostgreSQL** (Production):
```bash
DATABASE_URL=postgresql://user:password@host:5432/dbname
```
*Note: Ensure the `psycopg2` or `asyncpg` driver is installed if using Postgres.*
