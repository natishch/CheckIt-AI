"""
Pattern definitions and helper functions for router node.

This module centralizes all regex patterns, keyword lists, and helper functions
used by the router node for query classification and routing decisions.
"""

from __future__ import annotations

import re
from datetime import datetime
from re import Pattern

# ============================================================================
# Existing Patterns
# ============================================================================

# Non-historical request hints grouped by coarse intent type
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
        "python function",
        "write a python",
        "write a function",
        "write code",
        "code this",
        "bash script",
        "shell script",
        "powershell script",
        "dockerfile",
        "docker compose",
        "sql query",
        "regex for",
        "javascript function",
        "java function",
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
    "opinion_request": (
        "what's the best",
        "what is the best",
        "what's your favorite",
        "what is your favorite",
        "what's your favourite",
        "what is your favourite",
        "which is better",
        "which one is better",
        "do you prefer",
        "what do you think about",
        "what do you think of",
        "what's your opinion",
        "what is your opinion",
        "should i",
        "would you recommend",
        "what would you recommend",
        "top 10",
        "top ten",
        "best way to",
        "worst thing about",
        "favorite thing about",
        "favourite thing about",
    ),
}

# Very generic truth questions that need clarification
GENERIC_TRUTH_QUESTIONS = {
    "did it happen?",
    "is it true?",
    "is that true?",
    "is this true?",
}

# ============================================================================
# New Patterns
# ============================================================================

# Historical keywords for entity detection
HISTORICAL_KEYWORDS = [
    # Political
    "president",
    "king",
    "queen",
    "emperor",
    "pharaoh",
    "sultan",
    "chancellor",
    "prime minister",
    "dictator",
    "monarch",
    # Military
    "war",
    "battle",
    "siege",
    "invasion",
    "conquest",
    "crusade",
    "army",
    "navy",
    "general",
    "admiral",
    # Time periods
    "century",
    "era",
    "period",
    "age",
    "dynasty",
    "reign",
    "ancient",
    "medieval",
    "renaissance",
    # Events
    "revolution",
    "independence",
    "declaration",
    "treaty",
    "assassination",
    "coronation",
    # Institutions
    "empire",
    "kingdom",
    "republic",
    "confederation",
    "constitution",
    "parliament",
    "senate",
]

# ============================================================================
# Regex Patterns
# ============================================================================

# Year detection pattern
YEAR_PATTERN = re.compile(r"\b\d{3,4}(\s+(AD|BC|CE|BCE))?\b", re.IGNORECASE)

# Creative writing patterns
CREATIVE_WRITING_PATTERNS = [
    re.compile(
        r"\b(write|compose|create|generate)\s+(a|an|me)?\s*(poem|story|song|essay|lyrics)\b",
        re.IGNORECASE,
    ),
    re.compile(r"\b(imagine|fictional|storytelling)\b", re.IGNORECASE),
]

# Coding request patterns
CODING_PATTERNS = [
    re.compile(r"\b(code|function|class|script|program|debug|algorithm)\b", re.IGNORECASE),
    re.compile(r"\b(python|javascript|java|c\+\+|html|css|sql)\b", re.IGNORECASE),
    re.compile(r"```"),  # Code blocks
]

# Future prediction patterns
FUTURE_PREDICTION_PATTERNS = [
    re.compile(r"\b(will|gonna|going to)\s+.*\s+(happen|occur|be)\b", re.IGNORECASE),
    re.compile(r"\b(predict|forecast|future|upcoming)\b", re.IGNORECASE),
]

# Opinion request patterns
OPINION_PATTERNS = [
    re.compile(r"\b(think|feel|opinion|believe)\b.*\b(about|on)\b", re.IGNORECASE),
    re.compile(r"\b(should|better|best|worst|favorite)\b", re.IGNORECASE),
    re.compile(r"^(do you|can you)\s+(think|say|agree)\b", re.IGNORECASE),
]

# Pronoun-only clarification patterns
PRONOUN_ONLY_PATTERNS = [
    re.compile(r"^(it|that|this|he|she|they|when|where|what|who)\s*\??$", re.IGNORECASE),
    re.compile(r"^did\s+(it|that|this)\s+happen\s*\??$", re.IGNORECASE),
]

# Overly broad query patterns
OVERLY_BROAD_PATTERNS = [
    re.compile(r"^\b(history|past|events?|facts?)\b\s*\??$", re.IGNORECASE),
    re.compile(r"^(what|tell me)\s+(about|of)\s+(history|past)\s*\??$", re.IGNORECASE),
]

# Verification patterns (high priority fact-check)
VERIFICATION_PATTERNS = [
    re.compile(r"\b(is it true|true or false|fact or fiction)\b", re.IGNORECASE),
    re.compile(r"^(is|was|were|did)\b.*\b(true|correct|accurate|real|actually)\b", re.IGNORECASE),
    re.compile(r"^(verify|confirm|check)\b.*\b(that|whether|if)\b", re.IGNORECASE),
    re.compile(r"^did\b.*\breally\b", re.IGNORECASE),
]

# Language detection patterns (Hebrew + English only)
HEBREW_PATTERN = re.compile(r"[\u0590-\u05FF]")

# ============================================================================
# Helper Functions
# ============================================================================


def detect_language(query: str) -> str:
    """Detect query language: Hebrew ('he') or English ('en').

    Simple heuristic: If any Hebrew character found → 'he', else → 'en'

    Args:
        query: User query string

    Returns:
        Language code: 'he' for Hebrew, 'en' for English
    """
    if HEBREW_PATTERN.search(query):
        return "he"
    return "en"


def get_current_events_patterns(years_ago: int) -> list[Pattern]:
    """Generate current events patterns based on configuration.

    Args:
        years_ago: Number of years back to consider "current"
                   (0 = no filtering, allow all recent events)

    Returns:
        List of compiled regex patterns for detecting current events
    """
    if years_ago == 0:
        return []  # No current events filtering

    current_year = datetime.now().year
    recent_years = [str(y) for y in range(current_year - years_ago, current_year + 1)]

    return [
        re.compile(r"\b(latest|recent|now|current|breaking|trending)\b", re.IGNORECASE),
        re.compile(rf"\b({'|'.join(recent_years)})\b"),
        re.compile(r"\b(stock|bitcoin|weather|sports score)\b", re.IGNORECASE),
    ]


def has_historical_markers(query: str) -> bool:
    """Check if query contains historical entities or dates.

    Args:
        query: User query string (should be lowercased)

    Returns:
        True if historical markers detected, False otherwise
    """
    query_lower = query.lower()

    # Check for year patterns
    if YEAR_PATTERN.search(query):
        return True

    # Check for historical keywords
    return any(keyword in query_lower for keyword in HISTORICAL_KEYWORDS)


def is_verification_question(query: str) -> bool:
    """Check if query is an explicit verification request.

    Args:
        query: User query string

    Returns:
        True if verification patterns match, False otherwise
    """
    return any(pattern.search(query) for pattern in VERIFICATION_PATTERNS)
