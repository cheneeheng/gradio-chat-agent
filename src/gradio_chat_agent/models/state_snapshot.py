"""Data model for application state snapshots.

This module defines the schema for capturing the complete state of the
application's components at a specific point in time.
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class StateSnapshot(BaseModel):
    """Represents an immutable snapshot of the application state.

    Attributes:
        snapshot_id: Unique identifier for this snapshot.
        timestamp: When the snapshot was created.
        components: Dictionary mapping component IDs to their state objects.
    """

    snapshot_id: str = Field(
        ...,
        description="Unique identifier for this snapshot."
    )
    timestamp: datetime = Field(
        default_factory=datetime.now,
        description="When the snapshot was created."
    )
    components: dict[str, dict[str, Any]] = Field(
        default_factory=dict,
        description="Dictionary mapping component IDs to their state objects."
    )
