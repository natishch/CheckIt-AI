"""LLM module for Writer Node.

This module provides LLM provider factory, prompt utilities, and validation
functions for the writer node.
"""

from src.check_it_ai.llm.prompts import (
    FEW_SHOT_EXAMPLES,
    SYSTEM_PROMPT,
    build_few_shot_messages,
    build_user_prompt,
    format_evidence_for_prompt,
)
from src.check_it_ai.llm.providers import (
    LLMProviderError,
    check_provider_health,
    get_writer_llm,
)
from src.check_it_ai.llm.validation import (
    build_hallucination_correction_prompt,
    calculate_confidence,
    extract_citation_ids,
    validate_citations,
)

__all__ = [
    # Providers
    "get_writer_llm",
    "LLMProviderError",
    "check_provider_health",
    # Prompts
    "SYSTEM_PROMPT",
    "FEW_SHOT_EXAMPLES",
    "format_evidence_for_prompt",
    "build_user_prompt",
    "build_few_shot_messages",
    # Validation
    "extract_citation_ids",
    "validate_citations",
    "calculate_confidence",
    "build_hallucination_correction_prompt",
]
