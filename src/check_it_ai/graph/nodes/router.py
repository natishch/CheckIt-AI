from __future__ import annotations

from typing import Any, Tuple

import logging
import re

from src.check_it_ai.config import settings
from src.check_it_ai.graph.state import AgentState
SETTINGS=settings
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Non-historical intent hints
# ---------------------------------------------------------------------------

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

GENERIC_TRUTH_QUESTIONS = {
    "did it happen?",
    "is it true?",
    "is that true?",
    "is this true?",
}


def _analyze_query(q: str) -> dict[str, Any]:
    """Compute lightweight features for routing."""
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

    # Very lightweight ambiguous pronoun detection
    contains_ambiguous_pronoun = any(p in q_lower for p in (" this ", " that ", " it "))

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
    """
    for intent_type, hints in NON_HISTORICAL_HINTS.items():
        if any(h in q_lower for h in hints):
            return True, intent_type
    return False, ""


def router_node(state: AgentState) -> AgentState:
    """
    Decide route: fact_check vs clarify vs out_of_scope.

    Writes explanation and features into state.run_metadata["router"].
    """
    q = state.user_query or ""
    q_stripped = q.strip()
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
        state.run_metadata["router"] = meta
        return state

    # -----------------------------------------------------------------------
    # 2) Feature extraction
    # -----------------------------------------------------------------------
    features = _analyze_query(q)
    meta["features"] = features

    # -----------------------------------------------------------------------
    # 3) Non-historical detection (run BEFORE underspecified/clarify)
    # -----------------------------------------------------------------------
    is_non_hist, intent_type = _detect_non_historical_intent(q_lower)
    if is_non_hist:
        state.route = "out_of_scope"
        meta["route"] = state.route
        meta["reason_code"] = "non_historical_intent"
        meta["intent_type"] = intent_type  # "creative_request", "coding_request", "chat_request"
        meta["reason_text"] = (
            "Query appears to be non-historical (e.g., coding, creative writing, or general chat)."
        )
        state.run_metadata["router"] = meta
        if getattr(SETTINGS, "router_debug", False):
            logger.info(
                "Router: out_of_scope (%s)",
                intent_type,
                extra={"router_meta": meta},
            )
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
    state.run_metadata["router"] = meta
    if getattr(SETTINGS, "router_debug", False):
        logger.info("Router: fact_check", extra={"router_meta": meta})
    return state
