from __future__ import annotations

import logging
import re
from typing import Any

from src.check_it_ai.config import settings
from src.check_it_ai.graph.nodes.router_patterns import (
    GENERIC_TRUTH_QUESTIONS,
    NON_HISTORICAL_HINTS,
    YEAR_PATTERN,
    detect_language,
    has_historical_markers,
    is_verification_question,
)
from src.check_it_ai.graph.state import AgentState
from src.check_it_ai.types.clarify import ClarifyRequest
from src.check_it_ai.types.schemas import RouterDecision, RouterMetadata, RouterTrigger

SETTINGS = settings
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Feature extraction & intent detection
# ---------------------------------------------------------------------------
# NOTE: Pattern constants moved to router_patterns.py


def _analyze_query(q: str) -> dict[str, Any]:
    """
    Compute lightweight features for routing.

    Returns a dict that is also stored into run_metadata["router"]["features"].
    """
    q_stripped = q.strip()
    q_lower = q_stripped.lower()

    tokens = q_stripped.split()
    num_tokens = len(tokens)
    num_chars = len(q_stripped)

    starts_like_question = bool(
        re.match(
            r"^(when|what|who|where|why|how|did|was|were|is|are|can|could|would|should)\b",
            q_lower,
        )
    )

    # Very lightweight ambiguous pronoun detection:
    # note the spaces around to avoid matching inside words
    contains_ambiguous_pronoun = any(pat in q_lower for pat in (" this ", " that ", " it "))

    return {
        "num_tokens": num_tokens,
        "num_chars": num_chars,
        "starts_like_question": starts_like_question,
        "contains_ambiguous_pronoun": contains_ambiguous_pronoun,
    }


def _detect_non_historical_intent(q_lower: str) -> tuple[bool, str]:
    """
    Return (True, intent_type) if query appears non-historical.

    intent_type is one of:
        - "creative_request"
        - "coding_request"
        - "chat_request"
    or "" if no non-historical intent is detected.
    """
    for intent_type, hints in NON_HISTORICAL_HINTS.items():
        if any(h in q_lower for h in hints):
            return True, intent_type
    return False, ""


def _calculate_confidence(query: str) -> float:
    """Calculate routing confidence score (0.0-1.0) for fact-check decisions.

    Confidence is based on multiple signals:
    - Explicit verification patterns (highest weight)
    - Historical entities/dates
    - Question structure

    Confidence Tiers:
    - 0.85-1.0: Explicit verification + historical entity
    - 0.7-0.85: Strong historical signals (year + keywords + question)
    - 0.5-0.7:  Some historical signals
    - 0.3-0.5:  Weak signals (borderline)

    Args:
        query: User query string

    Returns:
        Float between 0.0 and 1.0
    """
    score = 0.3  # Conservative base

    # TIER 1: Explicit verification (strongest signal)
    if is_verification_question(query):
        score += 0.35
        if has_historical_markers(query):
            score += 0.2  # Verification + entity = very strong

    # TIER 2: Historical markers
    if YEAR_PATTERN.search(query):
        score += 0.15  # Contains year

    if has_historical_markers(query):
        score += 0.15  # Historical keywords

    # TIER 3: Question structure
    if re.search(r"\b(who|what|when|where|how|why)\b", query, re.IGNORECASE):
        score += 0.1  # WH-question

    if re.search(r"^(did|was|were|is|are)\b", query, re.IGNORECASE):
        score += 0.1  # Yes/no question

    return min(score, 1.0)


# ---------------------------------------------------------------------------
# Router node
# ---------------------------------------------------------------------------


def router_node(state: AgentState) -> AgentState:
    """
    Decide route: fact_check vs clarify vs out_of_scope.

    - Always writes a "router" entry into state.run_metadata using RouterMetadata
    - For route == "clarify", also populates state.clarify_request with a ClarifyRequest
    - For route in {"fact_check", "out_of_scope"}, clarify_request is left as None
    """

    # raw_query preserves original text including whitespace (important for clarify contract)
    raw_query = state.user_query or ""
    q_stripped = raw_query.strip()
    q_lower = q_stripped.lower()

    # Extract features for metadata
    features = _analyze_query(raw_query)
    query_length_words = features["num_tokens"]
    detected_language = detect_language(raw_query)

    # -----------------------------------------------------------------------
    # 1) Empty query -> clarify
    # -----------------------------------------------------------------------
    if not q_stripped:
        metadata = RouterMetadata(
            trigger=RouterTrigger.EMPTY_QUERY,
            decision=RouterDecision.CLARIFY,
            reasoning="Query is empty or whitespace",
            confidence=0.0,
            query_length_words=0,
            detected_language=detected_language,
            features=features,
        )

        state.route = "clarify"
        state.clarify_request = ClarifyRequest.from_empty_query(
            original_query=raw_query,
            features=features,
        )
        state.run_metadata["router"] = metadata.model_dump()
        return state

    # -----------------------------------------------------------------------
    # 2) Non-historical detection (run BEFORE underspecified/clarify)
    # -----------------------------------------------------------------------
    is_non_hist, intent_type = _detect_non_historical_intent(q_lower)
    if is_non_hist:
        # Out-of-scope has high confidence (pattern matched clearly)
        metadata = RouterMetadata(
            trigger=RouterTrigger.NON_HISTORICAL_INTENT,
            decision=RouterDecision.OUT_OF_SCOPE,
            reasoning=f"Non-historical request detected: {intent_type}",
            confidence=0.95,  # High confidence - clear pattern match
            query_length_words=query_length_words,
            detected_language=detected_language,
            features=features,
            intent_type=intent_type,
        )

        state.route = "out_of_scope"
        state.clarify_request = None
        state.run_metadata["router"] = metadata.model_dump()

        if getattr(SETTINGS, "router_debug", False):
            logger.info(
                "Router: out_of_scope (%s)",
                intent_type,
                extra={"router_meta": metadata.model_dump()},
            )
        return state

    # -----------------------------------------------------------------------
    # 3) Underspecified / ambiguous -> clarify
    # -----------------------------------------------------------------------
    if (
        features["num_chars"] < SETTINGS.router_min_query_chars
        or features["num_tokens"] < 2
        or q_lower in GENERIC_TRUTH_QUESTIONS
    ):
        # Clarify routes have low confidence by definition (need more info)
        metadata = RouterMetadata(
            trigger=RouterTrigger.UNDERSPECIFIED_QUERY,
            decision=RouterDecision.CLARIFY,
            reasoning="Query is too short or generic to form a specific historical claim",
            confidence=0.2,  # Low confidence - needs clarification
            query_length_words=query_length_words,
            detected_language=detected_language,
            features=features,
        )

        state.route = "clarify"
        state.clarify_request = ClarifyRequest.from_query(
            original_query=raw_query,
            reason_code="underspecified_query",
            features=features,
        )
        state.run_metadata["router"] = metadata.model_dump()

        if getattr(SETTINGS, "router_debug", False):
            logger.info(
                "Router: clarify (underspecified_query)",
                extra={"router_meta": metadata.model_dump()},
            )
        return state

    # Check for ambiguous pronouns, BUT skip if it's an explicit verification question
    # (e.g., "Is it true that..." has "it" but is a clear verification pattern)
    if features.get("contains_ambiguous_pronoun") and not is_verification_question(raw_query):
        metadata = RouterMetadata(
            trigger=RouterTrigger.AMBIGUOUS_REFERENCE,
            decision=RouterDecision.CLARIFY,
            reasoning="Query contains ambiguous pronouns (this/that/it) without clear context",
            confidence=0.3,  # Low confidence - needs clarification
            query_length_words=query_length_words,
            detected_language=detected_language,
            features=features,
        )

        state.route = "clarify"
        state.clarify_request = ClarifyRequest.from_query(
            original_query=raw_query,
            reason_code="ambiguous_reference",
            features=features,
        )
        state.run_metadata["router"] = metadata.model_dump()

        if getattr(SETTINGS, "router_debug", False):
            logger.info(
                "Router: clarify (ambiguous_reference)",
                extra={"router_meta": metadata.model_dump()},
            )
        return state

    # -----------------------------------------------------------------------
    # 4) Fact-check (with confidence scoring)
    # -----------------------------------------------------------------------
    # Check for explicit verification questions (highest priority)
    has_markers = has_historical_markers(raw_query)
    is_verification = is_verification_question(raw_query)

    if is_verification:
        trigger = RouterTrigger.EXPLICIT_VERIFICATION
        reasoning = "Explicit verification question detected"
    else:
        trigger = RouterTrigger.DEFAULT_FACT_CHECK
        reasoning = "Query passed all filters; routing to fact-check pipeline"

    # Calculate confidence score using the confidence function
    confidence = _calculate_confidence(raw_query)

    metadata = RouterMetadata(
        trigger=trigger,
        decision=RouterDecision.FACT_CHECK,
        reasoning=reasoning,
        confidence=confidence,  # Calculated based on signals
        query_length_words=query_length_words,
        has_historical_markers=has_markers,
        detected_language=detected_language,
        features=features,
    )

    state.route = "fact_check"
    state.clarify_request = None
    state.run_metadata["router"] = metadata.model_dump()

    if getattr(SETTINGS, "router_debug", False):
        logger.info("Router: fact_check", extra={"router_meta": metadata.model_dump()})

    return state
