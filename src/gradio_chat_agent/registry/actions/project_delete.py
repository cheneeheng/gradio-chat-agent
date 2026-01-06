from typing import Any

from gradio_chat_agent.execution.modes import ExecutionContext
from gradio_chat_agent.models.action import ActionDeclaration, ActionPermission
from gradio_chat_agent.persistence.auth_repo import AuthRepository
from gradio_chat_agent.persistence.repo import ProjectIdentity


def make_delete_action(auth_repo: AuthRepository) -> ActionDeclaration:
    return ActionDeclaration(
        action_id="project.delete",
        title="Delete project",
        description="Permanently deletes a project and all its data.",
        targets=["project"],
        input_schema={
            "type": "object",
            "properties": {"force": {"type": "boolean", "default": False}},
        },
        permission=ActionPermission(
            risk="high",
            confirmation_required=True,
            required_roles={"admin"},
            visibility="user",
        ),
        handler=lambda ctx, inputs, store: _handle_project_delete(
            ctx, inputs, auth_repo
        ),
    )


def _handle_project_delete(
    ctx: ExecutionContext,
    inputs: dict[str, Any],
    auth_repo: AuthRepository,
):
    if not inputs.get("force"):
        raise ValueError("Deletion requires force=true")

    auth_repo.clear_project(
        ProjectIdentity(
            user_id=ctx.user_id,
            project_id=int(ctx.project_id),
        )
    )

    return {
        "message": "Project deleted",
        "state_diff": [],
    }
