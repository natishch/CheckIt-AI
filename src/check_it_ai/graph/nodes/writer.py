
"""Writer node using fine-tuned LoRA model.

This node consumes the EvidenceBundle on AgentState and produces a
WriterOutput + final answer, enforcing evidence-grounded citations.

It is designed to work both with a real HF/LoRA backend and with simple
test stubs (via the generate_fn injection).
"""

from __future__ import annotations

import json
import re
import time
from typing import Any, Callable, Mapping

from src.check_it_ai.graph.state import AgentState
from src.check_it_ai.types.schemas import Citation, EvidenceBundle, EvidenceVerdict
from src.check_it_ai.types.writer import WriterOutput

# Simple pattern to detect citations like [E1], [E2], ...
_CITE_RE = re.compile(r"\[E\d+\]")


def _extract_citation_ids(text: str) -> set[str]:
    """Extract IDs like '[E1]', '[E2]' and return {'E1', 'E2'}."""
    matches = _CITE_RE.findall(text or "")
    return {m.strip("[]") for m in matches}


def _get_evidence_items(bundle: EvidenceBundle | None) -> list[Any]:
    """
    Helper to read evidence items from the bundle, handling both
    `evidence_items` and legacy `items` attributes.
    """
    if bundle is None:
        return []

    if hasattr(bundle, "evidence_items"):
        items = getattr(bundle, "evidence_items") or []
    else:
        items = getattr(bundle, "items", []) or []

    return list(items)


def writer_node(
    state: AgentState,
    generate_fn: Callable[[str], Mapping[str, Any]] | None = None,
) -> AgentState:
    """Generate final evidence-grounded response and update AgentState.

    Args:
        state: Current AgentState with evidence_bundle populated.
        generate_fn: Optional function(prompt) -> dict used for tests or
            pluggable backends. If None, the node will raise and fall back
            to a conservative answer (no live HF/LoRA wiring here).

    Returns:
        The updated AgentState (same instance, mutated).
    """
    start = time.perf_counter()
    writer_meta: dict[str, Any] = {}

    # ------------------------------------------------------------------
    # 1) No evidence at all -> conservative fallback, no LLM call
    # ------------------------------------------------------------------
    evidence_items = _get_evidence_items(state.evidence_bundle)
    if not evidence_items:
        wo = WriterOutput(
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

        state.writer_output = wo
        state.final_answer = wo.answer
        state.confidence = wo.confidence
        state.citations = []

        writer_meta.update(
            {
                "strategy": "no_evidence_fallback",
                "fallback_used": True,
                "citation_valid": True,
                "num_evidence_used": 0,
                "latency_seconds": time.perf_counter() - start,
            }
        )
        state.run_metadata["writer"] = writer_meta
        return state

    # ------------------------------------------------------------------
    # 2) Build prompt from evidence bundle
    # ------------------------------------------------------------------
    lines: list[str] = [
        "You are The Agentic Historian.",
        "",
        "Use ONLY the evidence items below to answer the user's question.",
        "Every factual statement MUST include at least one citation like [E1].",
        "",
        f"Question: {state.user_query}",
        "",
        "Evidence:",
    ]
    for e in evidence_items:
        # e has: id, title, snippet, url
        lines.append(f"{e.id}: {e.title} — {e.snippet} ({e.url})")

    prompt = "\n".join(lines)

    # ------------------------------------------------------------------
    # 3) Call generation backend (or test stub)
    # ------------------------------------------------------------------
    try:
        if generate_fn is None:
            # In the real system this would call HF/LoRA; here we force
            # tests to inject a stub.
            raise RuntimeError("No generate_fn provided; LLM backend not wired.")

        raw_output = generate_fn(prompt)
    except Exception as exc:  # generation failure -> fallback
        wo = WriterOutput(
            answer=(
                "I cannot verify this claim right now because the answer-generation model "
                "is currently unavailable."
            ),
            confidence=0.2,
            evidence_ids=[],
            limitations=f"Model failure: {exc}",
            verdict=EvidenceVerdict.INSUFFICIENT,
            citation_valid=True,
            fallback_used=True,
            raw_model_output=None,
        )

        state.writer_output = wo
        state.final_answer = wo.answer
        state.confidence = wo.confidence
        state.citations = []

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
        state.run_metadata["writer"] = writer_meta
        return state

    # ------------------------------------------------------------------
    # 4) Parse raw output into structured dict
    # ------------------------------------------------------------------
    if isinstance(raw_output, str):
        try:
            data: dict[str, Any] = json.loads(raw_output)
        except Exception:
            data = {"answer": raw_output}
    elif isinstance(raw_output, Mapping):
        data = dict(raw_output)
    else:
        data = {"answer": str(raw_output)}

    answer = (data.get("answer") or "").strip()
    confidence = float(data.get("confidence", 0.5))
    evidence_ids = list(data.get("evidence_ids") or [])
    limitations = data.get("limitations", "")

    # ------------------------------------------------------------------
    # 5) Determine default verdict from bundle
    # ------------------------------------------------------------------
    default_verdict = getattr(state.evidence_bundle, "overall_verdict", EvidenceVerdict.INSUFFICIENT)
    if isinstance(default_verdict, str):
        try:
            default_verdict = EvidenceVerdict.from_str(default_verdict)
        except Exception:
            default_verdict = EvidenceVerdict.INSUFFICIENT

    wo = WriterOutput(
        answer=answer or "I cannot provide an answer based on the current evidence.",
        confidence=max(0.0, min(1.0, confidence)),
        evidence_ids=evidence_ids,
        limitations=limitations,
        verdict=default_verdict,  # EvidenceVerdict
        raw_model_output=json.dumps(data, ensure_ascii=False),
    )

    # ------------------------------------------------------------------
    # 6) Citation extraction & validation
    # ------------------------------------------------------------------
    cited_ids_in_text = _extract_citation_ids(wo.answer)
    if not wo.evidence_ids and cited_ids_in_text:
        # Tests expect this behavior when evidence_ids is omitted
        wo.evidence_ids = sorted(cited_ids_in_text)

    available_ids = {e.id for e in evidence_items}
    unknown_ids = set(wo.evidence_ids) - available_ids

    citation_valid = bool(cited_ids_in_text) and not unknown_ids
    wo.citation_valid = citation_valid

    # Map IDs -> Citation objects if citations are valid
    citations: list[Citation] = []
    if wo.citation_valid:
        by_id = {e.id: e for e in evidence_items}
        for eid in wo.evidence_ids:
            item = by_id.get(eid)
            if item is not None:
                citations.append(
                    Citation(
                        evidence_id=eid,
                        url=item.url,
                        title=item.title,
                    )
                )

    # If citation invalid -> conservative fallback, clear IDs and citations
    if not wo.citation_valid:
        wo.fallback_used = True
        wo.answer = (
            "I cannot safely verify this claim using the retrieved evidence. "
            "The sources appear insufficient, inconsistent, or the citations are unclear."
        )
        if wo.limitations:
            wo.limitations = f"{wo.limitations} Citation validation failed."
        else:
            wo.limitations = "Citation validation failed."
        wo.confidence = min(wo.confidence, 0.3)
        wo.evidence_ids = []
        citations = []

    # ------------------------------------------------------------------
    # 7) Update AgentState
    # ------------------------------------------------------------------
    state.writer_output = wo
    state.final_answer = wo.answer
    state.confidence = wo.confidence
    state.citations = citations

    writer_meta.update(
        {
            "strategy": "llm_writer_with_fallback" if wo.fallback_used else "llm_writer",
            "fallback_used": wo.fallback_used,
            "citation_valid": wo.citation_valid,
            "num_evidence_used": len(wo.evidence_ids),
            "latency_seconds": time.perf_counter() - start,
        }
    )
    state.run_metadata["writer"] = writer_meta
    return state