"""Final output Pydantic schema."""

from pydantic import BaseModel, Field

from src.check_it_ai.types.evidence import Citation


class FinalOutput(BaseModel):
    """Final output schema with answer, citations, and confidence."""

    answer: str = Field(..., description="The final answer to the user query")
    citations: list[Citation] = Field(
        default_factory=list, description="Citations used in the answer"
    )
    confidence: float = Field(
        ..., ge=0.0, le=1.0, description="Confidence score between 0.0 and 1.0"
    )
    notes: str = Field(default="", description="Additional notes or limitations")
