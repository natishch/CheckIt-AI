"""Search-related Pydantic schemas."""

from pydantic import BaseModel, Field, HttpUrl


class SearchQuery(BaseModel):
    """Search query schema."""

    query: str = Field(..., min_length=1, description="Search query string")
    max_results: int = Field(default=10, ge=1, le=100, description="Maximum number of results")


class SearchResult(BaseModel):
    """Search result schema from Google Custom Search API."""

    title: str = Field(..., description="Title of the search result")
    snippet: str = Field(..., description="Snippet/preview text from the result")
    url: HttpUrl = Field(..., description="URL of the search result")
    display_domain: str = Field(..., description="Display domain (e.g., 'wikipedia.org')")
    rank: int = Field(..., ge=1, description="Rank position in search results")
