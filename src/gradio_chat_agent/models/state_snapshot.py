from datetime import datetime
from typing import Any

from pydantic import Field

from .base import ModelBase


class StateSnapshot(ModelBase):
    """
    Read-only snapshot of the current application state.
    """

    snapshot_id: str = Field(
        ...,
        description="Unique identifier for this snapshot.",
    )

    timestamp: datetime = Field(
        ...,
        description="Timestamp when the snapshot was taken.",
    )

    components: dict[str, dict[str, Any]] = Field(
        ...,
        description="Mapping from component_id to component state.",
    )
