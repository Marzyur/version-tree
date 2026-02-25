"""
Data models for the version tree system.
"""
from __future__ import annotations
from enum import Enum
from typing import Optional
from datetime import datetime
from pydantic import BaseModel, field_validator


class VersionType(str, Enum):
    """The three valid version types per spec."""
    TRUNK   = "TRUNK"
    BRANCH  = "BRANCH"
    RELEASE = "RELEASE"


class Version(BaseModel):
    """Represents a single version node in the tree."""
    id: str
    parent_id: Optional[str] = None
    name: str
    description: Optional[str] = None          # added per spec
    type: VersionType = VersionType.TRUNK       # TRUNK | BRANCH | RELEASE
    created_by: str = "unknown"
    created_at: datetime = datetime.now()

    @field_validator("id", "name")
    @classmethod
    def must_not_be_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Field must not be empty")
        return v.strip()


class LinearizedNode(BaseModel):
    """A version node enriched with tree-display metadata."""
    version: Version
    depth: int                          
    connectors: list[str]               # visual connector tokens per level
    ancestors: list[str]                # ordered list of ancestor IDs (root → parent)
    is_last_child: bool                 # whether this is the final child of its parent


class PageResponse(BaseModel):
    """Paginated API response."""
    page: int
    page_size: int
    total_nodes: int
    total_pages: int
    nodes: list[LinearizedNode]
    selected_id:Optional[str]=None
    highlighted_ids:list[str]=[]