"""Data model for application state snapshots.

This module defines the schema for capturing the complete state of the
application's components at a specific point in time.
"""

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


class StateSnapshot(BaseModel):
    """Represents a snapshot of the application state.

    Attributes:
        snapshot_id: Unique identifier for this snapshot.
        timestamp: When the snapshot was created.
        components: Dictionary mapping component IDs to their state objects.
        checksum: SHA-256 hash of the components dictionary.
        is_checkpoint: Whether this is a full-state checkpoint or a delta.
        parent_id: The ID of the previous snapshot this delta is relative to.
    """

    snapshot_id: str = Field(
        ..., description="Unique identifier for this snapshot."
    )
    timestamp: datetime = Field(
        default_factory=datetime.now,
        description="When the snapshot was created.",
    )
    components: dict[str, dict[str, Any]] = Field(
        default_factory=dict,
        description="Dictionary mapping component IDs to their state objects.",
    )
    checksum: Optional[str] = Field(
        default=None,
        description="SHA-256 hash of the components dictionary for integrity verification.",
    )
    is_checkpoint: bool = Field(
        default=True,
        description="Whether this is a full-state checkpoint or a delta.",
    )
    parent_id: Optional[str] = Field(
        default=None,
        description="The ID of the previous snapshot this delta is relative to.",
    )
