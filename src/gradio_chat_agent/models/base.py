from typing import Literal

from pydantic import BaseModel, ConfigDict


class ModelBase(BaseModel):
    """
    Base class for all gradio-chat-agent models.

    Enforces strict validation, forbids unknown fields,
    and enables assignment-time validation.
    """

    model_config = ConfigDict(
        extra="forbid",
        validate_assignment=True,
        frozen=False,
    )


ComponentId = str
ActionId = str
RequestId = str

RiskLevel = Literal["low", "medium", "high"]
Visibility = Literal["user", "developer"]
ExecutionStatus = Literal["success", "rejected", "failed"]
