"""Fact analyst node for evidence synthesis."""

from src.check_it_ai.graph.state import AgentState
from src.check_it_ai.types.schemas import EvidenceBundle


def fact_analyst_node(state: AgentState) -> dict:
    """Analyze search results and build evidence bundle.

    Returns:
        Dict with evidence_bundle: EvidenceBundle
    """
    # TODO: Implement actual evidence analysis logic
    # Placeholder returns empty EvidenceBundle
    evidence_bundle = EvidenceBundle(
        items=[],
        findings=[],
        overall_verdict="insufficient",
    )
    return {"evidence_bundle": evidence_bundle}
