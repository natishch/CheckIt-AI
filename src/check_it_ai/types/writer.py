"""Writer output schema.

This module contains the WriterOutput Pydantic model, which is the structured
result of the writer node.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from src.check_it_ai.types.evidence import EvidenceVerdict


class WriterOutput(BaseModel):
    """
    Structured result of the writer node.

    This is the single source of truth for what the UI should show as the final answer
    and what the evaluation harness should consume.
    """

    answer: str = Field(
        description=(
            "Final Markdown-formatted answer to show to the user, including [E#] "
            "citations that refer to EvidenceItem IDs."
        ),
    )

    confidence: float = Field(
        ge=0.0,
        le=1.0,
        description="Model's self-assessed confidence in the factual accuracy, between 0 and 1.",
    )

    evidence_ids: list[str] = Field(
        default_factory=list,
        description="EvidenceItem IDs actually used in the answer (e.g. ['E1', 'E3']).",
    )

    limitations: str = Field(
        default="",
        description="Short description of gaps, ambiguity, or contested points.",
    )

    verdict: EvidenceVerdict = Field(
        description=(
            "Writer's final verdict about the claim, typically mirroring "
            "evidence_bundle.overall_verdict."
        ),
    )

    citation_valid: bool = Field(
        default=True,
        description=(
            "True if citations in `answer` are consistent with `evidence_ids` and "
            "the current evidence bundle (no unknown [E#] and at least one citation "
            "when factual claims are made)."
        ),
    )

    fallback_used: bool = Field(
        default=False,
        description=(
            "True if a conservative fallback template was used due to missing/invalid "
            "citations or insufficient/contested evidence."
        ),
    )

    raw_model_output: str | None = Field(
        default=None,
        description=(
            "Optional raw text returned by the underlying LLM before parsing or "
            "citation validation, useful for debugging."
        ),
    )
