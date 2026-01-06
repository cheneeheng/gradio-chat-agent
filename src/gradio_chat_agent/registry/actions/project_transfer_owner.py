from typing import Any

from gradio_chat_agent.execution.modes import ExecutionContext
from gradio_chat_agent.models.action import ActionDeclaration, ActionPermission
from gradio_chat_agent.persistence.auth_repo import AuthRepository


def make_transfer_owner_action(auth_repo: AuthRepository) -> ActionDeclaration:
    return ActionDeclaration(
        action_id="project.transfer_owner",
        title="Transfer project ownership",
        description="Transfers admin ownership of the current project to another user.",
        targets=["project"],
        input_schema={
            "type": "object",
            "properties": {
                "new_owner_username": {"type": "string"},
            },
            "required": ["new_owner_username"],
        },
        permission=ActionPermission(
            risk="high",
            confirmation_required=True,
            visibility="user",
            required_roles={"admin"},
        ),
        handler=lambda ctx, inputs, store: _handle_transfer_owner(
            ctx, inputs, auth_repo
        ),
    )


def _handle_transfer_owner(
    ctx: ExecutionContext,
    inputs: dict[str, Any],
    auth_repo: AuthRepository,
):
    new_owner = auth_repo.get_user(inputs["new_owner_username"])
    if new_owner is None:
        raise ValueError("Target user does not exist")

    # Transfer ownership
    auth_repo.ensure_membership(
        user_id=new_owner.user_id,
        project_id=int(ctx.project_id),
        role="admin",
    )

    # Downgrade current owner to operator
    auth_repo.ensure_membership(
        user_id=ctx.user_id,
        project_id=int(ctx.project_id),
        role="operator",
    )

    return {
        "message": f"Ownership transferred to {inputs['new_owner_username']}",
        "state_diff": [],
    }

