from __future__ import annotations

import logging
import re
from typing import Any

from src.check_it_ai.config import settings
from src.check_it_ai.graph.state import AgentState
from src.check_it_ai.types.clarify import ClarifyRequest
SETTINGS=settings
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants & heuristics
# ---------------------------------------------------------------------------

# Non-historical request hints grouped by a coarse intent type
NON_HISTORICAL_HINTS: dict[str, tuple[str, ...]] = {
    "creative_request": (
        "write me a poem",
        "poem about",
        "song about",
        "lyrics about",
        "short story",
        "story about",
        "screenplay",
        "script for",
    ),
    "coding_request": (
        "python code",
        "python script",
        "write a python script",
        "write code",
        "code this",
        "bash script",
        "shell script",
        "powershell script",
        "dockerfile",
        "docker compose",
        "sql query",
        "regex for",
    ),
    "chat_request": (
        "tell me a joke",
        "make me laugh",
        "roast me",
        "pick up line",
        "pickup line",
        "dating advice",
        "relationship advice",
        "life advice",
    ),
}

# Very generic truth questions that need clarification
GENERIC_TRUTH_QUESTIONS = {
    "did it happen?",
    "is it true?",
    "is that true?",
    "is this true?",
}


# ---------------------------------------------------------------------------
# Feature extraction & intent detection
# ---------------------------------------------------------------------------


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
    contains_ambiguous_pronoun = any(
        pat in q_lower for pat in (" this ", " that ", " it ")
    )

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


# ---------------------------------------------------------------------------
# Router node
# ---------------------------------------------------------------------------


def router_node(state: AgentState) -> AgentState:
    """
    Decide route: fact_check vs clarify vs out_of_scope.

    - Always writes a "router" entry into state.run_metadata.
    - For route == "clarify", also populates state.clarify_request with a ClarifyRequest.
    - For route in {"fact_check", "out_of_scope"}, clarify_request is left as None.
    """

    # raw_query preserves original text including whitespace (important for clarify contract)
    raw_query = state.user_query or ""
    q_stripped = raw_query.strip()
    q_lower = q_stripped.lower()

    meta: dict[str, Any] = {
        "route": None,
        "reason_code": None,
        "reason_text": None,
        "features": {},
    }

    # -----------------------------------------------------------------------
    # 1) Empty query -> clarify
    # -----------------------------------------------------------------------
    if not q_stripped:
        state.route = "clarify"
        meta["route"] = state.route
        meta["reason_code"] = "empty_query"
        meta["reason_text"] = "Query is empty or whitespace."

        # ClarifyRequest with original (including spaces)
        state.clarify_request = ClarifyRequest.from_empty_query(
            original_query=raw_query,
            features=None,
        )

        state.run_metadata["router"] = meta
        return state

    # -----------------------------------------------------------------------
    # 2) Feature extraction
    # -----------------------------------------------------------------------
    features = _analyze_query(raw_query)
    meta["features"] = features

    # -----------------------------------------------------------------------
    # 3) Non-historical detection (run BEFORE underspecified/clarify)
    # -----------------------------------------------------------------------
    is_non_hist, intent_type = _detect_non_historical_intent(q_lower)
    if is_non_hist:
        state.route = "out_of_scope"
        meta["route"] = state.route
        meta["reason_code"] = "non_historical_intent"
        meta["intent_type"] = intent_type
        meta["reason_text"] = (
            "Query appears to be non-historical (e.g., coding, creative writing, or general chat)."
        )
        # clarify_request MUST stay None here
        state.clarify_request = None

        state.run_metadata["router"] = meta
        if getattr(SETTINGS, "router_debug", False):
            logger.info("Router: out_of_scope (%s)", intent_type, extra={"router_meta": meta})
        return state

    # -----------------------------------------------------------------------
    # 4) Underspecified / ambiguous -> clarify
    # -----------------------------------------------------------------------
    if (
        features["num_chars"] < 8
        or features["num_tokens"] < 2
        or q_lower in GENERIC_TRUTH_QUESTIONS
    ):
        state.route = "clarify"
        meta["route"] = state.route
        meta["reason_code"] = "underspecified_query"
        meta["reason_text"] = "Query is too short or generic to form a specific historical claim."

        state.clarify_request = ClarifyRequest.from_query(
            original_query=raw_query,
            reason_code="underspecified_query",
            features=features,
        )

        state.run_metadata["router"] = meta
        if getattr(SETTINGS, "router_debug", False):
            logger.info(
                "Router: clarify (underspecified_query)",
                extra={"router_meta": meta},
            )
        return state

    if features.get("contains_ambiguous_pronoun"):
        state.route = "clarify"
        meta["route"] = state.route
        meta["reason_code"] = "ambiguous_reference"
        meta["reason_text"] = (
            "Query uses ambiguous reference like 'this/that/it' without clear context."
        )

        state.clarify_request = ClarifyRequest.from_query(
            original_query=raw_query,
            reason_code="ambiguous_reference",
            features=features,
        )

        state.run_metadata["router"] = meta
        if getattr(SETTINGS, "router_debug", False):
            logger.info(
                "Router: clarify (ambiguous_reference)",
                extra={"router_meta": meta},
            )
        return state

    # -----------------------------------------------------------------------
    # 5) Default -> fact_check
    # -----------------------------------------------------------------------
    state.route = "fact_check"
    meta["route"] = state.route
    meta["reason_code"] = "default_fact_check"
    meta["reason_text"] = "Default: treat as a historical fact-check question."
    state.clarify_request = None  # no clarify contract on fact_check path

    state.run_metadata["router"] = meta
    if getattr(SETTINGS, "router_debug", False):
        logger.info("Router: fact_check", extra={"router_meta": meta})

    return state
