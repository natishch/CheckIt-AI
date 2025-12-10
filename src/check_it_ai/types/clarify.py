# src/agentic_historian/types/clarify.py
from __future__ import annotations

from typing import Literal
from pydantic import BaseModel, Field


# Which “slots” we might ask the user to fill in
ClarifyFieldKey = Literal["claim", "entity", "event", "time_period", "location"]

# Why we are in clarify mode
ClarifyReasonCode = Literal[
    "empty_query",
    "underspecified_query",
    "ambiguous_reference",
    "other",
]


class ClarifyField(BaseModel):
    """
    A single clarification field the UI can render.

    Example:
        key="claim",
        question="What exactly do you want me to verify?",
        hint="E.g. 'Did the Berlin Wall fall in 1989?'"
    """

    key: ClarifyFieldKey
    question: str
    hint: str | None = None


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
    ) -> ClarifyRequest:
        """
        Build a ClarifyRequest when the user query is empty/whitespace.
        `features` is optional and mainly there to keep the signature symmetrical
        with from_query().
        """
        _ = features  # not used currently, kept for forward-compatibility

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
    ) -> ClarifyRequest:
        """
        Build a ClarifyRequest for underspecified or ambiguous queries.

        Expected `reason_code` values here are typically:
        - 'underspecified_query'
        - 'ambiguous_reference'
        but we keep the signature generic.

        `features` is the dict produced by the router analysis, e.g.:
           {
             "normalized": "...",
             "has_historical_keyword": True,
             ...
           }
        """
        features = features or {}
        normalized = features.get("normalized", original_query.lower())
        _ = normalized  # not strictly needed yet, but kept for future heuristics

        # Base fields: always ask for a clear claim
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

        # If we detected some historical keyword and the issue is underspecification,
        # ask for a time period as well.
        has_hist_keyword = bool(features.get("has_historical_keyword"))
        if has_hist_keyword and reason_code == "underspecified_query":
            fields.append(
                ClarifyField(
                    key="time_period",
                    question="For which time period or date should I check this?",
                    hint="If you know an approximate year or era, that helps reduce ambiguity.",
                )
            )

        if reason_code == "underspecified_query":
            message = (
                "Your question is a bit too short for me to identify a specific historical claim."
            )
        elif reason_code == "ambiguous_reference":
            message = (
                "I am not sure what 'this/that/it' refers to in your question. "
                "Please specify the historical event, person, or claim."
            )
        else:
            message = (
                "I need a bit more detail to understand the historical claim you want me to check."
            )

        # Normalize reason_code into the allowed Literal set
        normalized_reason: ClarifyReasonCode
        if reason_code in ("empty_query", "underspecified_query", "ambiguous_reference"):
            normalized_reason = reason_code
        else:
            normalized_reason = "other"

        return cls(
            reason_code=normalized_reason,
            original_query=original_query,
            message=message,
            fields=fields,
        )

