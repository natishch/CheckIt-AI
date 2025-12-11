from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Public types
# ---------------------------------------------------------------------------

ClarifyReasonCode = Literal["empty_query", "underspecified_query", "ambiguous_reference"]


class ClarifyField(BaseModel):
    """
    Single input field requested from the user to clarify their query.
    """

    key: str = Field(description="Stable key, e.g. 'claim'.")
    question: str = Field(description="Human-facing question, e.g. 'What exactly happened?'.")
    hint: str | None = Field(
        default=None,
        description="Optional example or hint for the user.",
    )
    required: bool = Field(
        default=True,
        description="Whether this field must be filled in.",
    )


class ClarifyRequest(BaseModel):
    """
    Contract used when route == 'clarify'.

    The router node fills this when it cannot construct a precise historical
    claim to fact-check. The UI should:

      1. Show `message` to the user.
      2. Render `fields` as follow-up questions.

    Example shape:

    ClarifyRequest(
        reason_code="underspecified_query",
        message="Your question is a bit too short...",
        original_query="is it true?",
        fields=[
            ClarifyField(
                key="claim",
                question="What exactly do you want me to verify?",
                hint="For example: 'Did X happen in year Y?'"
            )
        ]
    )
    """

    reason_code: ClarifyReasonCode
    message: str
    original_query: str = ""
    fields: list[ClarifyField] = Field(default_factory=list)

    # -------------------------------------------------------------------------
    # Convenience constructors used by the router node
    # -------------------------------------------------------------------------

    @classmethod
    def from_empty_query(
        cls,
        original_query: str,
        features: dict | None = None,
    ) -> "ClarifyRequest":
        """
        Build a ClarifyRequest when the user query is empty/whitespace.
        `features` is optional and mainly there to keep the signature symmetrical
        with from_query().
        """
        _ = features  # currently unused

        return cls(
            reason_code="empty_query",
            original_query=original_query,
            message=(
                "Please type a historical claim or question you would like me to fact-check."
            ),
            fields=[
                ClarifyField(
                    key="claim",
                    question="What historical event, person, or claim should I check?",
                    hint="For example: 'Did the Berlin Wall fall in 1989?'",
                )
            ],
        )

    @classmethod
    def from_query(
        cls,
        original_query: str,
        reason_code: ClarifyReasonCode,
        features: dict | None = None,
    ) -> "ClarifyRequest":
        """
        Build a ClarifyRequest for underspecified or ambiguous queries.

        Expected `reason_code` values here are typically:
        - 'underspecified_query'
        - 'ambiguous_reference'
        """
        features = features or {}

        # Base field: always ask for a clear claim
        fields: list[ClarifyField] = [
            ClarifyField(
                key="claim",
                question="What exactly do you want me to verify?",
                hint=(
                    "For example: 'Did X happen in year Y?' or "
                    "'Was person P involved in event E?'"
                ),
            )
        ]

        # Optional: if later you add 'has_historical_keyword' to features,
        # you can add a second field for time period, but tests don't require it.

        # Messages tuned to match clarify tests
        if reason_code == "underspecified_query":
            # tests look for 'too short' or 'bit too short'
            message = (
                "Your question is a bit too short for me to identify a specific historical claim."
            )
        elif reason_code == "ambiguous_reference":
            message = (
                "I am not sure what 'this/that/it' refers to in your question. "
                "Please specify the historical event, person, or claim."
            )
        else:
            # For completeness if we ever call this with 'empty_query'
            message = (
                "I need a bit more detail to understand the historical claim you want me to check."
            )

        return cls(
            reason_code=reason_code,
            original_query=original_query,
            message=message,
            fields=fields,
        )
