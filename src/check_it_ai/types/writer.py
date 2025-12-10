from __future__ import annotations

from typing import List
from pydantic import BaseModel, Field
from src.check_it_ai.types.schemas import EvidenceVerdict
import json
import re
from typing import Any

#from src.check_it_ai.llm.prompts import build_writer_prompt

CITE_RE = re.compile(r"\[E\d+\]")

class WriterOutput(BaseModel):
    """
    Structured result of the writer node.

    This is the single source of truth for what the UI should show as the final answer
    and what the evaluation harness should consume.
    """

    answer: str = Field(
        description=(
            "Final Markdown-formatted answer to show to the user, including [E#] "
            "citations that refer to EvidenceItem IDs."
        ),
    )

    confidence: float = Field(
        ge=0.0,
        le=1.0,
        description="Model's self-assessed confidence in the factual accuracy, between 0 and 1.",
    )

    evidence_ids: List[str] = Field(
        default_factory=list,
        description="EvidenceItem IDs actually used in the answer (e.g. ['E1', 'E3']).",
    )

    limitations: str = Field(
        default="",
        description="Short description of gaps, ambiguity, or contested points.",
    )

    verdict: EvidenceVerdict = Field(
        description=(
            "Writer's final verdict about the claim, typically mirroring "
            "evidence_bundle.overall_verdict."
        ),
    )

    citation_valid: bool = Field(
        default=True,
        description=(
            "True if citations in `answer` are consistent with `evidence_ids` and "
            "the current evidence bundle (no unknown [E#] and at least one citation "
            "when factual claims are made)."
        ),
    )

    fallback_used: bool = Field(
        default=False,
        description=(
            "True if a conservative fallback template was used due to missing/invalid "
            "citations or insufficient/contested evidence."
        ),
    )

    raw_model_output: str | None = Field(
        default=None,
        description=(
            "Optional raw text returned by the underlying LLM before parsing or "
            "citation validation, useful for debugging."
        ),
    )


def _extract_citation_ids(text: str) -> set[str]:
    """
    Extract IDs like '[E1]', '[E2]' and return {'E1', 'E2'}.
    """
    matches = CITE_RE.findall(text)
    return {m.strip("[]") for m in matches}


def _call_llm(prompt: str) -> str:
    """
    Placeholder for HF + PEFT/LoRA call.
    Ideally, you instruct the model to return JSON with:
    {
      "answer": "...",
      "confidence": 0.8,
      "evidence_ids": ["E1","E3"],
      "limitations": "..."
    }
    """
    # TODO: integrate actual HF/PEFT client
    raise NotImplementedError


def _parse_llm_output(raw: str, default_verdict: EvidenceVerdict) -> WriterOutput:
    """
    Parse raw model output into WriterOutput.
    Assumes JSON if possible, otherwise falls back to a minimal structure.
    """
    try:
        data = json.loads(raw)
        answer = data.get("answer", raw)
        confidence = float(data.get("confidence", 0.5))
        evidence_ids = list(data.get("evidence_ids", []))
        limitations = data.get("limitations", "")
    except Exception:
        # Fallback: whole raw text is the answer
        answer = raw
        confidence = 0.5
        evidence_ids = []
        limitations = ""

    return WriterOutput(
        answer=answer,
        confidence=confidence,
        evidence_ids=evidence_ids,
        limitations=limitations,
        verdict=default_verdict,
        raw_model_output=raw,
    )


def writer_node(state: AgentState) -> AgentState:
    if not state.evidence_bundle:
        # No evidence; emit a conservative fallback directly
        wo = WriterOutput(
            answer=(
                "I cannot verify this claim because I could not retrieve any relevant evidence. "
                "Please refine your question or try again later."
            ),
            confidence=0.2,
            evidence_ids=[],
            limitations="No evidence bundle available.",
            verdict="insufficient",
            citation_valid=True,
            fallback_used=True,
            raw_model_output=None,
        )
        state.writer_output = wo
        state.final_answer = wo.answer
        state.run_metadata["writer"] = {
            "confidence": wo.confidence,
            "evidence_ids": wo.evidence_ids,
            "verdict": wo.verdict,
            "citation_valid": wo.citation_valid,
            "fallback_used": wo.fallback_used,
        }
        return state

    # Build prompt from evidence
    prompt = build_writer_prompt(state.user_query, state.evidence_bundle)

    # Call model
    raw = _call_llm(prompt)

    # Parse structured output
    default_verdict: EvidenceVerdict = state.evidence_bundle.overall_verdict
    wo = _parse_llm_output(raw, default_verdict=default_verdict)

    # Validate citations
    available_ids = {e.id for e in state.evidence_bundle.evidence_items}
    cited_ids_in_text = _extract_citation_ids(wo.answer)
    unknown_ids = cited_ids_in_text - available_ids

    # If LLm didn't provide evidence_ids, infer from text
    if not wo.evidence_ids:
        wo.evidence_ids = sorted(cited_ids_in_text)

    # Basic citation validity rules
    citation_valid = bool(cited_ids_in_text) and not unknown_ids
    wo.citation_valid = citation_valid

    # If citations invalid or empty but evidence exists -> fallback
    if not wo.citation_valid:
        wo.fallback_used = True
        wo.answer = (
            "I can't safely verify this claim using the retrieved evidence. "
            "The sources appear insufficient, inconsistent, or the citations are unclear."
        )
        wo.confidence = min(wo.confidence, 0.3)
        wo.evidence_ids = []

    # Update state
    state.writer_output = wo
    state.final_answer = wo.answer
    state.run_metadata["writer"] = {
        "confidence": wo.confidence,
        "evidence_ids": wo.evidence_ids,
        "verdict": wo.verdict,
        "citation_valid": wo.citation_valid,
        "fallback_used": wo.fallback_used,
    }

    return state
