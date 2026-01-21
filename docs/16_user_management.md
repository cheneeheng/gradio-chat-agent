# User & Role Management

## Overview

Access to projects and actions is governed by a **Role-Based Access Control (RBAC)** system. This document outlines how users are managed and how roles are assigned.

---

## Roles

The system supports three fixed roles per project:

1.  **Viewer (`viewer`)**:
    *   Can view chat history and state.
    *   Can **NOT** execute any actions.
    *   Safe for stakeholders who only need observability.

2.  **Operator (`operator`)**:
    *   Can execute `low` and `medium` risk actions.
    *   Can execute `confirmation_required` actions (with explicit confirmation).
    *   Subject to standard budget limits.

3.  **Admin (`admin`)**:
    *   Full control over the project.
    *   Can execute `high` risk actions.
    *   Can manage project settings and membership.
    *   Can override approval blocks.

---

## Managing Users

### CLI Management
The primary way to bootstrap users in a production environment is via the CLI tools (if implemented) or direct database scripts.

```bash
# Example: Create a new user (via conceptual CLI)
uv run python -m gradio_chat_agent.tools.users create --username alice --password "securepassword"
```

### In-App Management (Admin Only)
If logged in as an **Admin**, the UI exposes a "Team" or "Settings" tab.

1.  **Invite User**: Enter a username to add them to the current project.
2.  **Assign Role**: Select `viewer`, `operator`, or `admin` from the dropdown.
3.  **Remove User**: Revoke access to the project.

---

## Initial Setup (Bootstrap)

On the very first run, the application creates a default super-admin:
*   **Username**: `admin`
*   **Password**: `admin` (Change this immediately!)

**Security Warning**: In production, you should disable this auto-creation behavior via the `ALLOW_DEFAULT_ADMIN=False` environment variable (if implemented) or pre-seed the database.
