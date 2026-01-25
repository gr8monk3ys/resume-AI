"""
Pagination schemas for list endpoints.

Provides reusable pagination parameters and response wrappers
to prevent memory issues with large datasets.
"""

from math import ceil
from typing import Generic, List, Optional, TypeVar

from fastapi import Query
from pydantic import BaseModel, Field

# Generic type for paginated items
T = TypeVar("T")

# Constants for pagination limits
DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100
MIN_PAGE_SIZE = 1


class PaginationParams:
    """
    Pagination parameters for list endpoints.

    Can be used as a FastAPI dependency to extract pagination
    parameters from query strings.

    Example:
        @router.get("/items")
        async def list_items(
            pagination: PaginationParams = Depends(),
        ):
            items = db.query(Item).offset(pagination.skip).limit(pagination.limit).all()
    """

    def __init__(
        self,
        page: int = Query(
            default=1,
            ge=1,
            description="Page number (1-indexed)",
        ),
        limit: int = Query(
            default=DEFAULT_PAGE_SIZE,
            ge=MIN_PAGE_SIZE,
            le=MAX_PAGE_SIZE,
            description=f"Number of items per page (max {MAX_PAGE_SIZE})",
        ),
    ):
        self.page = page
        self.limit = limit

    @property
    def skip(self) -> int:
        """Calculate the offset for database queries."""
        return (self.page - 1) * self.limit


class PaginatedResponse(BaseModel, Generic[T]):
    """
    Generic paginated response wrapper.

    Provides pagination metadata along with the items list
    for frontend pagination UI components.

    Attributes:
        items: List of items for the current page
        total: Total number of items across all pages
        page: Current page number (1-indexed)
        limit: Number of items per page
        pages: Total number of pages
        has_next: Whether there is a next page
        has_prev: Whether there is a previous page
    """

    items: List[T]
    total: int = Field(..., description="Total number of items")
    page: int = Field(..., ge=1, description="Current page number")
    limit: int = Field(..., ge=1, description="Items per page")
    pages: int = Field(..., ge=0, description="Total number of pages")
    has_next: bool = Field(..., description="Whether there is a next page")
    has_prev: bool = Field(..., description="Whether there is a previous page")

    class Config:
        from_attributes = True

    @classmethod
    def create(
        cls,
        items: List[T],
        total: int,
        page: int,
        limit: int,
    ) -> "PaginatedResponse[T]":
        """
        Factory method to create a paginated response.

        Args:
            items: List of items for the current page
            total: Total count of all items
            page: Current page number
            limit: Items per page

        Returns:
            PaginatedResponse with computed pagination metadata
        """
        pages = ceil(total / limit) if total > 0 else 0
        return cls(
            items=items,
            total=total,
            page=page,
            limit=limit,
            pages=pages,
            has_next=page < pages,
            has_prev=page > 1,
        )
