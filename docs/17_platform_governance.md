# Platform Governance

## Overview

Platform Governance defines the global authority layer that sits above individual projects. This is required for bootstrapping the system, managing infrastructure-level limits, and cross-project observability.

---

## Global Authority: The System Admin

While Project Admins manage their own scope, **System Admins** have platform-wide permissions:

*   **Project Lifecycle**: Creating, Archiving, and Purging projects.
*   **Global User Registry**: Provisioning new users.
*   **Global Observability**: Viewing `api_org_rollup` for all users.
*   **Policy Templating**: Defining the default rate limits and budgets for new projects.

---

## Project Lifecycle

### 1. Creation
Projects are created via `api_manage_project(op="create")`.
*   A unique `project_id` is assigned.
*   Default policies are copied from the System Template.
*   The creator is assigned the `admin` role for that project.

### 2. Archival
Archiving a project (`archived_at != null`) disables the Execution Engine for all actions but preserves the Audit Log and Snapshots for compliance.

### 3. Deletion (Purge)
A purge is a destructive operation. All rows in `executions`, `snapshots`, and `session_facts` for that `project_id` are deleted. This usually requires a high-risk confirmation gate.

---

## Policy Management

Governance policies (defined in `docs/policies/`) can be updated at runtime:

1.  **YAML Definition**: Developers/Admins define limits in YAML.
2.  **Promotion**: The `api_update_project_policy` endpoint parses the YAML/JSON and updates the authoritative database records (`project_limits` table).
3.  **Hot Reload**: The Execution Engine reads limits on every request, ensuring policy changes take effect immediately without a restart.
