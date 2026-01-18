"""CLI tool for managing the Gradio Chat Agent."""

import json
import os
from pathlib import Path
from typing import Optional

import typer
import yaml
from jsonschema import validate as json_validate
from jsonschema.exceptions import ValidationError as JsonSchemaValidationError
from typing_extensions import Annotated

from gradio_chat_agent.persistence.sql_repository import SQLStateRepository
from gradio_chat_agent.utils import hash_password


app = typer.Typer(help="Gradio Chat Agent Management CLI")
project_app = typer.Typer(help="Manage projects")
user_app = typer.Typer(help="Manage users")
webhook_app = typer.Typer(help="Manage webhooks")
token_app = typer.Typer(help="Manage API tokens")

app.add_typer(project_app, name="project")
app.add_typer(user_app, name="user")
app.add_typer(webhook_app, name="webhook")
app.add_typer(token_app, name="token")


def get_repo():
    db_url = os.environ.get(
        "DATABASE_URL", "sqlite:///gradio_chat_agent.sqlite3"
    )
    return SQLStateRepository(db_url)


@project_app.command("create")
def project_create(
    name: Annotated[str, typer.Option(help="Project name")],
    project_id: Annotated[
        Optional[str], typer.Option(help="Optional project ID")
    ] = None,
):
    """Creates a new project."""
    repo = get_repo()
    pid = project_id or name.lower().replace(" ", "-")
    repo.create_project(pid, name)
    typer.echo(f"Project created: {name} (ID: {pid})")


@project_app.command("list")
def project_list():
    """Lists all projects."""
    repo = get_repo()
    projects = repo.list_projects()
    if not projects:
        typer.echo("No projects found.")
        return

    for p in projects:
        status = "Archived" if p["archived"] else "Active"
        typer.echo(f"[{status}] {p['id']}: {p['name']}")


@project_app.command("validate")
def project_validate(
    file_path: Annotated[
        Path, typer.Argument(help="Path to policy YAML file")
    ],
):
    """Validates a project policy YAML file against the schema."""
    if not file_path.exists():
        typer.echo(f"Error: File not found: {file_path}", err=True)
        raise typer.Exit(code=1)

    try:
        with open(file_path, "r") as f:
            policy = yaml.safe_load(f)
    except Exception as e:
        typer.echo(f"Error parsing YAML: {str(e)}", err=True)
        raise typer.Exit(code=1)

    schema_path = (
        Path(__file__).parent.parent.parent
        / "docs"
        / "schemas"
        / "policy.schema.json"
    )
    if not schema_path.exists():
        # Fallback if running from a different environment
        typer.echo(
            "Warning: Policy schema not found for validation. Skipping schema check.",
            err=True,
        )
        return

    try:
        with open(schema_path, "r") as f:
            schema = json.load(f)
        json_validate(instance=policy, schema=schema)
        typer.echo(f"Policy file {file_path} is valid.")
    except JsonSchemaValidationError as e:
        typer.echo(f"Validation Error: {e.message}", err=True)
        if e.path:
            typer.echo(f"Path: {'.'.join(str(p) for p in e.path)}", err=True)
        raise typer.Exit(code=1)
    except Exception as e:
        typer.echo(f"Error: {str(e)}", err=True)
        raise typer.Exit(code=1)


@user_app.command("create")
def user_create(
    username: Annotated[str, typer.Option(help="Username")],
    password: Annotated[
        str, typer.Option(help="Password", prompt=True, hide_input=True)
    ],
):
    """Creates a new user."""
    repo = get_repo()
    password_hash = hash_password(password)
    repo.create_user(username, password_hash)
    typer.echo(f"User created: {username}")


@user_app.command("password-reset")
def user_password_reset(
    username: Annotated[str, typer.Option(help="Username")],
    new_password: Annotated[
        str, typer.Option(help="New Password", prompt=True, hide_input=True)
    ],
):
    """Resets a user's password."""
    repo = get_repo()
    password_hash = hash_password(new_password)
    repo.update_user_password(username, password_hash)
    typer.echo(f"Password updated for user: {username}")


@webhook_app.command("list")
def webhook_list(
    project_id: Annotated[
        Optional[str], typer.Option(help="Filter by project ID")
    ] = None,
):
    """Lists all webhooks."""
    repo = get_repo()
    webhooks = repo.list_webhooks(project_id)
    if not webhooks:
        typer.echo("No webhooks found.")
        return

    for w in webhooks:
        status = "Enabled" if w["enabled"] else "Disabled"
        typer.echo(
            f"[{status}] {w['id']} (Project: {w['project_id']}, Action: {w['action_id']})"
        )


@token_app.command("create")
def token_create(
    owner: Annotated[str, typer.Option(help="Username of the token owner")],
    name: Annotated[str, typer.Option(help="Label for the token")],
    expires_days: Annotated[
        Optional[int], typer.Option(help="Days until expiration")
    ] = None,
):
    """Creates a new API token."""
    repo = get_repo()
    import uuid
    from datetime import datetime, timedelta

    token_id = f"sk-{uuid.uuid4().hex}"
    expires_at = None
    if expires_days:
        expires_at = datetime.utcnow() + timedelta(days=expires_days)

    repo.create_api_token(owner, name, token_id, expires_at)
    typer.echo(f"Token created: {name}")
    typer.echo(f"Value: {token_id}")
    if expires_at:
        typer.echo(f"Expires at: {expires_at}")


@token_app.command("list")
def token_list(
    owner: Annotated[str, typer.Option(help="Username of the token owner")],
):
    """Lists all API tokens for a user."""
    repo = get_repo()
    tokens = repo.list_api_tokens(owner)
    if not tokens:
        typer.echo(f"No tokens found for user: {owner}")
        return

    for t in tokens:
        status = "Active" if not t["revoked_at"] else "Revoked"
        typer.echo(f"[{status}] {t['id']}: {t['name']}")


@token_app.command("revoke")
def token_revoke(
    token_id: Annotated[str, typer.Argument(help="The token ID to revoke")],
):
    """Revokes an API token."""
    repo = get_repo()
    repo.revoke_api_token(token_id)
    typer.echo(f"Token revoked: {token_id}")


if __name__ == "__main__":
    app()
