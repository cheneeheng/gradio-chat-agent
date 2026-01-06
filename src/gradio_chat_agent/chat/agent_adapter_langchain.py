from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Union
from uuid import uuid4

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import Runnable
from langchain_openai import ChatOpenAI

from ..execution.modes import ExecutionMode
from ..execution.plan import ExecutionPlan
from ..models.action import ActionDeclaration
from ..models.component import ComponentDeclaration
from ..models.intent import ChatIntent
from ..persistence.memory_repo import MemoryRepository
from ..persistence.repo import ProjectIdentity, StateRepository
from .memory import build_memory_block
from .tools import ProposeActionCall, ProposeExecutionPlan


SYSTEM_PROMPT = """You are the control-plane agent for a Gradio UI.

Hard rules:
- You MUST only choose action_ids from the provided action registry.
- You MUST respect action preconditions and action input_schema.
- You MUST consult the current state snapshot before choosing an action.
- You MUST NOT guess. If ambiguous or missing required inputs, ask a clarification question.
- Use ProposeExecutionPlan only when multiple dependent steps are clearly required.
- confirmed=True ONLY if the user explicitly confirmed in chat.

Notes:
- The execution engine enforces authorization. You may propose actions the user might not be allowed to execute,
  but prefer proposing actions that match the user's role when possible.
"""


class LangChainAgentAdapter:
    def __init__(
        self,
        *,
        model_name: str = "gpt-4o-mini",
        temperature: float = 0.0,
        default_mode: ExecutionMode = "interactive",
        components: dict[str, ComponentDeclaration],
        actions: dict[str, ActionDeclaration],
        repo: StateRepository,
        mem_repo: MemoryRepository,
    ) -> None:
        self.default_mode = default_mode
        self.components = components
        self.actions = actions
        self.repo = repo
        self.mem_repo = mem_repo

        self.llm: Runnable = ChatOpenAI(
            model=model_name, temperature=temperature
        ).bind_tools(
            [ProposeActionCall, ProposeExecutionPlan],
            tool_choice="auto",
        )

        self.prompt = ChatPromptTemplate.from_messages(
            [
                ("system", SYSTEM_PROMPT),
                ("system", "Project context: project_id={project_id}"),
                ("system", "User roles: {user_roles}"),
                ("system", "Session memory:\n{memory_block}"),
                ("system", "Component registry:\n{components_block}"),
                ("system", "Action registry:\n{actions_block}"),
                (
                    "human",
                    "User message:\n{user_message}\n\nCurrent state:\n{state_block}",
                ),
            ]
        )

    def _components_block(self) -> str:
        lines: list[str] = []
        for c in self.components.values():
            lines.append(f"- component_id: {c.component_id}")
            lines.append(f"  title: {c.title}")
            lines.append(f"  description: {c.description}")
            lines.append(f"  state_schema: {c.state_schema}")
        return "\n".join(lines)

    def _actions_block(self) -> str:
        lines: list[str] = []
        for a in self.actions.values():
            lines.append(f"- action_id: {a.action_id}")
            lines.append(f"  title: {a.title}")
            lines.append(f"  description: {a.description}")
            lines.append(f"  targets: {a.targets}")
            lines.append(
                "  permission: "
                f"risk={a.permission.risk}, "
                f"confirmation_required={a.permission.confirmation_required}, "
                f"required_roles={sorted(a.permission.required_roles)}"
            )
            lines.append(f"  input_schema: {a.input_schema}")
            if a.preconditions:
                lines.append("  preconditions:")
                for p in a.preconditions:
                    lines.append(f"    - id: {p.id}")
                    lines.append(f"      description: {p.description}")
                    lines.append(f"      expr: {p.expr}")
            else:
                lines.append("  preconditions: []")
        return "\n".join(lines)

    def message_to_intent_or_plan(
        self,
        *,
        message: str,
        state: dict[str, dict[str, Any]],
        execution_mode: ExecutionMode | None,
        ident: ProjectIdentity,
        user_roles: list[str],
    ) -> Union[ChatIntent, ExecutionPlan]:
        mode: ExecutionMode = execution_mode or self.default_mode  # pyright: ignore[reportAssignmentType]
        memory_block = build_memory_block(
            self.repo, self.mem_repo, ident, limit=12
        )

        chain = self.prompt | self.llm
        response = chain.invoke(
            {
                "project_id": ident.project_id,
                "user_roles": user_roles,
                "memory_block": memory_block,
                "components_block": self._components_block(),
                "actions_block": self._actions_block(),
                "user_message": message,
                "state_block": repr(state),
            }
        )

        if getattr(response, "tool_calls", None):
            tool_call = response.tool_calls[0]
            tool_name = tool_call["name"]
            tool_args = tool_call["args"]

            if tool_name == "ProposeActionCall":
                proposal = ProposeActionCall.model_validate(tool_args)
                request_id = tool_call.get("id") or str(uuid4())
                return ChatIntent(
                    type="action_call",
                    request_id=request_id,
                    timestamp=datetime.now(timezone.utc),
                    execution_mode=mode,
                    action_id=proposal.action_id,
                    inputs=proposal.inputs,
                    confirmed=proposal.confirmed,
                    trace={
                        "source": "langchain",
                        "tool": "ProposeActionCall",
                        "tool_call_id": tool_call.get("id"),
                    },
                )

            if tool_name == "ProposeExecutionPlan":
                proposal = ProposeExecutionPlan.model_validate(tool_args)
                steps: list[ChatIntent] = []
                for i, s in enumerate(proposal.steps):
                    steps.append(
                        ChatIntent(
                            type="action_call",
                            request_id=f"{proposal.plan_id}:{i}:{uuid4()}",
                            timestamp=datetime.now(timezone.utc),
                            execution_mode=mode,
                            action_id=s.action_id,
                            inputs=s.inputs,
                            confirmed=s.confirmed,
                            trace={
                                "source": "langchain",
                                "tool": "ProposeExecutionPlan",
                                "plan_id": proposal.plan_id,
                                "step_index": i,
                            },
                        )
                    )
                return ExecutionPlan(plan_id=proposal.plan_id, steps=steps)

        text = getattr(response, "content", "") or ""
        question = (
            text.strip()
            or "I need clarification to choose an action and required inputs."
        )
        return ChatIntent(
            type="clarification_request",
            request_id=f"clarify:{uuid4()}",
            timestamp=datetime.now(timezone.utc),
            execution_mode=mode,
            question=question,
            choices=list(self.actions.keys()),
            trace={"source": "langchain", "reason": "no_tool_call"},
        )
