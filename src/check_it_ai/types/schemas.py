"""Pydantic schemas for structured data."""

from pydantic import BaseModel


class SearchResult(BaseModel):
    """Search result schema."""

    title: str
    snippet: str
    url: str


class EvidenceBundle(BaseModel):
    """Evidence bundle schema."""

    verdict: str = "insufficient"
