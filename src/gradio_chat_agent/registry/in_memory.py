from typing import Any

from ..models.action import (
    ActionDeclaration,
    ActionEffects,
    ActionPermission,
    ActionPrecondition,
)
from ..models.component import ComponentDeclaration, ComponentPermissions
from ..models.execution_result import StateDiffEntry
from ..models.state_snapshot import StateSnapshot
from .actions.project_delete import make_delete_action
from .actions.project_transfer_owner import make_transfer_owner_action


def build_component_registry() -> dict[str, ComponentDeclaration]:
    return {
        "demo.counter": ComponentDeclaration(
            component_id="demo.counter",
            title="Counter",
            description="A demo counter to prove chat-controlled state mutation works.",
            state_schema={
                "type": "object",
                "description": "State for the counter component.",
                "required": ["value"],
                "properties": {
                    "value": {
                        "type": "integer",
                        "description": "Current counter value.",
                    }
                },
                "additionalProperties": False,
            },
            permissions=ComponentPermissions(
                readable=True, writable_via_actions_only=True
            ),
            invariants=["value is an integer"],
            tags=["demo"],
        )
    }


def build_action_registry() -> dict[str, ActionDeclaration]:
    return {
        "demo.counter.set": ActionDeclaration(
            action_id="demo.counter.set",
            title="Set counter value",
            description="Sets the demo counter to an explicit integer value.",
            targets=["demo.counter"],
            input_schema={
                "type": "object",
                "description": "Inputs for setting the demo counter.",
                "required": ["value"],
                "properties": {
                    "value": {
                        "type": "integer",
                        "description": "New counter value.",
                    }
                },
                "additionalProperties": False,
            },
            preconditions=[],
            effects=ActionEffects(
                may_change=["components.demo.counter.value"]
            ),
            permission=ActionPermission(
                confirmation_required=False,
                risk="low",
                visibility="user",
                required_roles=set(),  # any user
            ),
        ),
        "demo.counter.increment": ActionDeclaration(
            action_id="demo.counter.increment",
            title="Increment counter",
            description="Increments the demo counter by delta (default 1).",
            targets=["demo.counter"],
            input_schema={
                "type": "object",
                "description": "Inputs for incrementing the counter.",
                "properties": {
                    "delta": {
                        "type": "integer",
                        "description": "Amount to increment by.",
                        "default": 1,
                    }
                },
                "additionalProperties": False,
            },
            preconditions=[
                ActionPrecondition(
                    id="demo.counter.exists",
                    description="Counter component must exist in state.",
                    expr='"demo.counter" in components',
                )
            ],
            effects=ActionEffects(
                may_change=["components.demo.counter.value"]
            ),
            permission=ActionPermission(
                confirmation_required=False,
                risk="low",
                visibility="user",
                required_roles={"admin"},
            ),
        ),
        "project.transfer_owner": make_transfer_owner_action(auth_repo),
        "project.delete": make_delete_action(auth_repo),
        "project.archive": ActionDeclaration(
            action_id="project.archive",
            title="Archive project",
            description="Archives the project. Execution is disabled but data is preserved.",
            targets=["project"],
            input_schema={"type": "object", "properties": {}},
            permission=ActionPermission(
                risk="high",
                confirmation_required=True,
                required_roles={"admin"},
            ),
        ),
        "project.restore": ActionDeclaration(
            action_id="project.restore",
            title="Restore project",
            description="Restores an archived project.",
            targets=["project"],
            input_schema={"type": "object", "properties": {}},
            permission=ActionPermission(
                risk="high",
                confirmation_required=True,
                required_roles={"admin"},
            ),
        ),
    }


def build_action_handlers():
    def counter_set(inputs: dict[str, Any], snapshot: StateSnapshot):
        cur = dict(snapshot.components)
        counter = dict(cur.get("demo.counter", {"value": 0}))
        old = counter.get("value", 0)
        new = int(inputs["value"])
        counter["value"] = new
        cur["demo.counter"] = counter
        diff = [
            StateDiffEntry(
                path="components.demo.counter.value", op="replace", value=new
            )
        ]
        return cur, diff, f"Counter changed from {old} to {new}"

    def counter_increment(inputs: dict[str, Any], snapshot: StateSnapshot):
        cur = dict(snapshot.components)
        counter = dict(cur.get("demo.counter", {"value": 0}))
        delta = int(inputs.get("delta", 1))
        old = int(counter.get("value", 0))
        new = old + delta
        counter["value"] = new
        cur["demo.counter"] = counter
        diff = [
            StateDiffEntry(
                path="components.demo.counter.value", op="replace", value=new
            )
        ]
        return cur, diff, f"Counter incremented by {delta} to {new}"

    return {
        "demo.counter.set": counter_set,
        "demo.counter.increment": counter_increment,
    }
