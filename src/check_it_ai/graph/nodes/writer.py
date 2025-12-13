"""Writer node for evidence-grounded fact-checking responses.

This node consumes the EvidenceBundle on AgentState and produces a
WriterOutput + final answer, enforcing evidence-grounded citations.

It supports:
1. Real LLM calls via the llm module (providers + prompts)
2. Hybrid confidence scoring
3. Citation validation with re-prompt strategy
"""

from __future__ import annotations

import json
import time
from collections.abc import Mapping
from typing import Any

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from src.check_it_ai.config import settings
from src.check_it_ai.graph.state import AgentState
from src.check_it_ai.llm.prompts import SYSTEM_PROMPT, build_few_shot_messages, build_user_prompt
from src.check_it_ai.llm.providers import get_writer_llm
from src.check_it_ai.llm.validation import (
    calculate_confidence,
    validate_citations,
)
from src.check_it_ai.types.evidence import Citation, EvidenceBundle, EvidenceVerdict
from src.check_it_ai.types.writer import WriterOutput


def _get_evidence_items(bundle: EvidenceBundle | None) -> list[Any]:
    """Helper to read evidence items from the bundle.

    Handles both `evidence_items` and legacy `items` attributes.
    """
    if bundle is None:
        return []

    if hasattr(bundle, "evidence_items"):
        items = bundle.evidence_items or []
    else:
        items = getattr(bundle, "items", []) or []

    return list(items)


def _parse_llm_output(raw_output: str | Mapping[str, Any]) -> dict[str, Any]:
    """Parse raw LLM output into a structured dict.

    Args:
        raw_output: Either a JSON string or a Mapping from the LLM.

    Returns:
        Dict with answer, confidence (-1.0 if not provided), evidence_ids, limitations.
        A confidence of -1.0 indicates the LLM did not provide a confidence value.
    """
    if isinstance(raw_output, str):
        try:
            data: dict[str, Any] = json.loads(raw_output)
        except Exception:
            data = {"answer": raw_output}
    elif isinstance(raw_output, Mapping):
        data = dict(raw_output)
    else:
        data = {"answer": str(raw_output)}

    return {
        "answer": (data.get("answer") or "").strip(),
        "confidence": float(data.get("confidence", -1.0)),
        "evidence_ids": list(data.get("evidence_ids") or []),
        "limitations": data.get("limitations", ""),
        "raw": data,
    }


def _build_citations(
    evidence_ids: list[str],
    evidence_items: list[Any],
) -> list[Citation]:
    """Build Citation objects from evidence IDs and items.

    Args:
        evidence_ids: List of evidence IDs to include.
        evidence_items: List of EvidenceItem objects.

    Returns:
        List of Citation objects for the cited evidence.
    """
    by_id = {e.id: e for e in evidence_items}
    citations = []
    for eid in evidence_ids:
        item = by_id.get(eid)
        if item is not None:
            citations.append(
                Citation(
                    evidence_id=eid,
                    url=item.url,
                    title=item.title,
                )
            )
    return citations


def _create_no_evidence_fallback() -> WriterOutput:
    """Create fallback output when no evidence is available."""
    return WriterOutput(
        answer=(
            "I cannot verify this claim because I could not retrieve any relevant evidence. "
            "Please refine your question or try again later."
        ),
        confidence=0.2,
        evidence_ids=[],
        limitations="No evidence bundle or the bundle contained no items.",
        verdict=EvidenceVerdict.INSUFFICIENT,
        citation_valid=True,
        fallback_used=True,
        raw_model_output=None,
    )


def _create_error_fallback(error: Exception) -> WriterOutput:
    """Create fallback output when LLM call fails."""
    return WriterOutput(
        answer=(
            "I cannot verify this claim right now because the answer-generation model "
            "is currently unavailable."
        ),
        confidence=0.2,
        evidence_ids=[],
        limitations=f"Model failure: {error}",
        verdict=EvidenceVerdict.INSUFFICIENT,
        citation_valid=True,
        fallback_used=True,
        raw_model_output=None,
    )


def _create_citation_invalid_fallback(
    original_limitations: str,
    original_confidence: float,
) -> dict[str, Any]:
    """Create fallback values when citations are invalid."""
    if original_limitations:
        limitations = f"{original_limitations} Citation validation failed."
    else:
        limitations = "Citation validation failed."

    return {
        "answer": (
            "I cannot safely verify this claim using the retrieved evidence. "
            "The sources appear insufficient, inconsistent, or the citations are unclear."
        ),
        "confidence": min(original_confidence, 0.3),
        "limitations": limitations,
        "evidence_ids": [],
        "fallback_used": True,
    }


def _build_messages(user_prompt: str) -> list:
    """Build the full message list for LLM invocation.

    Args:
        user_prompt: The user prompt containing evidence and question.

    Returns:
        List of messages: [system, few-shot examples..., user].
    """
    messages = [SystemMessage(content=SYSTEM_PROMPT)]

    # Add few-shot examples
    for msg in build_few_shot_messages():
        if msg["role"] == "user":
            messages.append(HumanMessage(content=msg["content"]))
        else:
            messages.append(AIMessage(content=msg["content"]))

    # Add the actual user prompt
    messages.append(HumanMessage(content=user_prompt))
    return messages


def writer_node(
    state: AgentState,
    llm: BaseChatModel | None = None,
) -> dict[str, Any]:
    """Generate final evidence-grounded response and return state updates.

    Args:
        state: Current AgentState with evidence_bundle populated.
        llm: Optional LLM instance. If None, uses get_writer_llm(settings).

    Returns:
        Dict with state updates: writer_output, final_answer, confidence,
        citations, and run_metadata.
    """
    start = time.perf_counter()
    writer_meta: dict[str, Any] = {}

    # ------------------------------------------------------------------
    # 1) No evidence at all -> conservative fallback, no LLM call
    # ------------------------------------------------------------------
    evidence_items = _get_evidence_items(state.evidence_bundle)
    if not evidence_items:
        wo = _create_no_evidence_fallback()
        writer_meta.update(
            {
                "strategy": "no_evidence_fallback",
                "fallback_used": True,
                "citation_valid": True,
                "num_evidence_used": 0,
                "latency_seconds": time.perf_counter() - start,
            }
        )
        return {
            "writer_output": wo,
            "final_answer": wo.answer,
            "confidence": wo.confidence,
            "citations": [],
            "run_metadata": {**state.run_metadata, "writer": writer_meta},
        }

    # ------------------------------------------------------------------
    # 2) Get LLM instance (use provided or create from settings)
    # ------------------------------------------------------------------
    if llm is None:
        llm = get_writer_llm(settings)

    # ------------------------------------------------------------------
    # 3) Build messages and call LLM
    # ------------------------------------------------------------------
    user_prompt = build_user_prompt(state.user_query, state.evidence_bundle)
    messages = _build_messages(user_prompt)

    try:
        response = llm.invoke(messages)
        raw_output = response.content
    except Exception as exc:
        wo = _create_error_fallback(exc)
        writer_meta.update(
            {
                "strategy": "generation_error_fallback",
                "fallback_used": True,
                "citation_valid": True,
                "num_evidence_used": 0,
                "latency_seconds": time.perf_counter() - start,
                "error": str(exc),
            }
        )
        return {
            "writer_output": wo,
            "final_answer": wo.answer,
            "confidence": wo.confidence,
            "citations": [],
            "run_metadata": {**state.run_metadata, "writer": writer_meta},
        }

    # ------------------------------------------------------------------
    # 4) Parse raw output into structured dict
    # ------------------------------------------------------------------
    parsed = _parse_llm_output(raw_output)
    answer = parsed["answer"]
    llm_confidence = parsed["confidence"]
    evidence_ids = parsed["evidence_ids"]
    limitations = parsed["limitations"]

    # ------------------------------------------------------------------
    # 5) Get verdict from bundle (Pydantic ensures it's already EvidenceVerdict)
    # ------------------------------------------------------------------
    verdict = state.evidence_bundle.overall_verdict

    # ------------------------------------------------------------------
    # 6) Citation extraction & validation using llm.validation
    # ------------------------------------------------------------------
    validation = validate_citations(answer, state.evidence_bundle)
    cited_ids = validation["cited_ids"]

    # If LLM didn't provide evidence_ids, infer from text
    if not evidence_ids and cited_ids:
        evidence_ids = sorted(cited_ids)

    # ------------------------------------------------------------------
    # 7) Calculate confidence using hybrid approach
    # ------------------------------------------------------------------
    confidence = calculate_confidence(
        llm_confidence=llm_confidence,
        evidence_bundle=state.evidence_bundle,
        cited_ids=cited_ids,
    )

    # ------------------------------------------------------------------
    # 8) Build WriterOutput
    # ------------------------------------------------------------------
    wo = WriterOutput(
        answer=answer or "I cannot provide an answer based on the current evidence.",
        confidence=confidence,
        evidence_ids=evidence_ids,
        limitations=limitations,
        verdict=verdict,
        citation_valid=validation["is_valid"],
        raw_model_output=json.dumps(parsed["raw"], ensure_ascii=False),
    )

    # ------------------------------------------------------------------
    # 9) Build citations if valid
    # ------------------------------------------------------------------
    citations: list[Citation] = []
    if wo.citation_valid:
        citations = _build_citations(wo.evidence_ids, evidence_items)

    # ------------------------------------------------------------------
    # 10) Handle invalid citations -> fallback
    # ------------------------------------------------------------------
    if not wo.citation_valid:
        fallback = _create_citation_invalid_fallback(wo.limitations, wo.confidence)
        wo.answer = fallback["answer"]
        wo.confidence = fallback["confidence"]
        wo.limitations = fallback["limitations"]
        wo.evidence_ids = fallback["evidence_ids"]
        wo.fallback_used = fallback["fallback_used"]
        citations = []

    # ------------------------------------------------------------------
    # 11) Return state updates
    # ------------------------------------------------------------------
    writer_meta.update(
        {
            "strategy": "llm_writer_with_fallback" if wo.fallback_used else "llm_writer",
            "fallback_used": wo.fallback_used,
            "citation_valid": wo.citation_valid,
            "num_evidence_used": len(wo.evidence_ids),
            "latency_seconds": time.perf_counter() - start,
        }
    )

    return {
        "writer_output": wo,
        "final_answer": wo.answer,
        "confidence": wo.confidence,
        "citations": citations,
        "run_metadata": {**state.run_metadata, "writer": writer_meta},
    }
