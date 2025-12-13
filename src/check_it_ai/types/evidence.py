"""Evidence-related Pydantic schemas for fact-checking."""

import re
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator


class EvidenceItem(BaseModel):
    """Individual evidence item with citation ID."""

    id: str = Field(..., description="Evidence ID in format 'E1', 'E2', etc.")
    title: str = Field(..., description="Source title")
    snippet: str = Field(..., description="Relevant snippet from the source")
    url: HttpUrl = Field(..., description="Source URL")
    # Optional in constructors; we can derive it from the URL later if needed.
    display_domain: str = Field(
        default="",
        description="Display domain of the source (e.g., 'wikipedia.org').",
    )

    @field_validator("id")
    @classmethod
    def validate_evidence_id(cls, v: str) -> str:
        """Validate evidence ID format: must be 'E' followed by digits."""
        if not re.match(r"^E\d+$", v):
            raise ValueError(f"Evidence ID must match pattern 'E<number>', got: {v}")
        return v


class EvidenceVerdict(StrEnum):
    """
    Normalized verdict for a historical claim based on the collected evidence.

    Values:
        SUPPORTED      – The evidence strongly supports the claim.
        NOT_SUPPORTED  – The evidence contradicts or fails to support the claim.
        CONTESTED      – The evidence is conflicting across sources.
        INSUFFICIENT   – There is not enough evidence to decide either way.
    """

    SUPPORTED = "supported"
    NOT_SUPPORTED = "not_supported"
    CONTESTED = "contested"
    INSUFFICIENT = "insufficient"

    @classmethod
    def from_str(cls, value: str) -> "EvidenceVerdict":
        """
        Lenient string-to-enum converter. Accepts common variants like:
        'Supported', 'NOT_SUPPORTED', 'contested', etc.
        Raises ValueError on unknown values.
        """
        normalized = value.strip().lower()

        mapping = {
            "supported": cls.SUPPORTED,
            "support": cls.SUPPORTED,
            "true": cls.SUPPORTED,
            "not_supported": cls.NOT_SUPPORTED,
            "not supported": cls.NOT_SUPPORTED,
            "false": cls.NOT_SUPPORTED,
            "contested": cls.CONTESTED,
            "mixed": cls.CONTESTED,
            "insufficient": cls.INSUFFICIENT,
            "unknown": cls.INSUFFICIENT,
        }

        try:
            return mapping[normalized]
        except KeyError:
            raise ValueError(f"Unknown EvidenceVerdict value: {value!r}") from None


class Finding(BaseModel):
    """A finding with a claim, verdict, and supporting evidence IDs."""

    claim: str = Field(..., description="The claim being evaluated")
    verdict: EvidenceVerdict

    evidence_ids: list[str] = Field(
        default_factory=list, description="List of evidence IDs supporting this finding"
    )

    @field_validator("evidence_ids")
    @classmethod
    def validate_evidence_ids(cls, v: list[str]) -> list[str]:
        """Validate all evidence IDs in the list."""
        for evidence_id in v:
            if not re.match(r"^E\d+$", evidence_id):
                raise ValueError(f"Evidence ID must match pattern 'E<number>', got: {evidence_id}")
        return v


class EvidenceBundle(BaseModel):
    """Complete evidence bundle with items, findings, and overall verdict.

    Notes
    -----
    - `evidence_items` is the canonical field used in new code.
    - `items` is kept as an alias for backward compatibility.
    """

    model_config = ConfigDict(populate_by_name=True)

    evidence_items: list[EvidenceItem] = Field(
        default_factory=list,
        description="List of evidence items",
        alias="items",
    )
    findings: list[Finding] = Field(
        default_factory=list,
        description="List of findings with verdicts",
    )
    overall_verdict: EvidenceVerdict = Field(
        default=EvidenceVerdict.INSUFFICIENT,
        description="Overall verdict based on all findings",
    )

    @property
    def items(self) -> list[EvidenceItem]:
        """Backward compatible attribute; returns `evidence_items`."""
        return self.evidence_items


class Citation(BaseModel):
    """Citation linking evidence ID to URL."""

    evidence_id: str = Field(..., description="Evidence ID being cited")
    url: HttpUrl = Field(..., description="URL of the cited source")
    title: str = Field(
        default="",
        description="Title of the cited source (for UI display).",
    )

    @field_validator("evidence_id")
    @classmethod
    def validate_evidence_id(cls, v: str) -> str:
        """Validate evidence ID format: must be 'E' followed by digits."""
        if not re.match(r"^E\d+$", v):
            raise ValueError(f"Evidence ID must match pattern 'E<number>', got: {v}")
        return v
