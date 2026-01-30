"""Data models for standardized API responses."""

from typing import Generic, Optional, TypeVar

from pydantic import BaseModel


T = TypeVar("T")


class ApiResponse(BaseModel, Generic[T]):
    """Standardized envelope for all API responses.

    Attributes:
        code: Machine-readable status code (0 for success).
        message: Human-readable status message.
        data: The actual payload of the response.
    """

    code: int = 0
    message: str = "success"
    data: Optional[T] = None
