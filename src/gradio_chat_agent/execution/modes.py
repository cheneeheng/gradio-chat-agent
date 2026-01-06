from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


ExecutionMode = Literal["interactive", "assisted", "autonomous"]


class ModePolicy(BaseModel):
    """
    Governs how the execution engine behaves under a given execution mode.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    mode: ExecutionMode = Field(
        ...,
        description="Execution mode controlling agent autonomy and safety gates.",
    )

    max_steps: int = Field(
        8,
        description="Maximum number of execution steps allowed in a single plan.",
        ge=1,
    )

    allow_schema_defaults: bool = Field(
        True,
        description="Whether schema defaults may be applied automatically.",
    )

    stop_on_ambiguity: bool = Field(
        default=True,
        description="Whether execution must halt when ambiguity is detected.",
    )

    require_confirmation_for_high_risk: bool = Field(
        default=True,
        description="Whether high-risk actions always require confirmation.",
    )

    @classmethod
    def for_mode(cls, mode: ExecutionMode) -> "ModePolicy":
        match mode:
            case "interactive":
                return cls(
                    mode=mode,
                    max_steps=4,
                    allow_schema_defaults=False,
                )
            case "assisted":
                return cls(
                    mode=mode,
                    max_steps=6,
                    allow_schema_defaults=True,
                )
            case "autonomous":
                return cls(
                    mode=mode,
                    max_steps=8,
                    allow_schema_defaults=True,
                )
            case _:
                raise ValueError(f"Unknown execution mode: {mode}")


class ExecutionContext(BaseModel):
    """
    Per-request execution context enforcing execution-mode constraints.
    """

    model_config = ConfigDict(extra="forbid")

    policy: ModePolicy
    step_index: int = Field(
        default=0,
        description="Current execution step index.",
        ge=0,
    )
    plan_id: str | None = Field(
        default=None,
        description="Optional identifier for a multi-step execution plan.",
    )
    user_id: str = Field(
        ..., description="Authenticated user identifier for this request."
    )
    user_roles: list[str] = Field(
        default_factory=list,
        description="Roles associated with user_id for authorization checks.",
    )

    def next_step(self) -> "ExecutionContext":
        return self.model_copy(update={"step_index": self.step_index + 1})

    def validate_step_limit(self) -> None:
        if self.step_index >= self.policy.max_steps:
            raise RuntimeError(
                f"Step limit reached ({self.step_index}/{self.policy.max_steps})"
            )
