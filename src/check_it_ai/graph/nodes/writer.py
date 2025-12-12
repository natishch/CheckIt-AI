"""Writer node using fine-tuned LoRA model."""

from src.check_it_ai.graph.state import AgentState
from src.check_it_ai.types.schemas import Citation


def writer_node(state: AgentState) -> dict:
    """Generate final evidence-grounded response.

    Returns:
        Dict with final_answer: str, citations: list[Citation], confidence: float
    """
    # TODO: Implement actual LLM-based answer generation
    # Placeholder returns empty response
    final_answer = "Placeholder answer - awaiting implementation"
    citations: list[Citation] = []
    confidence = 0.0

    return {
        "final_answer": final_answer,
        "citations": citations,
        "confidence": confidence,
    }
