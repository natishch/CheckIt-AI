import random

from src.check_it_ai.types.evidence import Citation, EvidenceItem
from src.check_it_ai.types.output import FinalOutput


def create_evidence_item(
    source_url: str, snippet: str, title: str = "Source Title", publish_date: str = "2023-10-27"
) -> EvidenceItem:
    """Helper to create an EvidenceItem."""
    return EvidenceItem(
        id=f"E{random.randint(1000, 99999)}",  # Changed to random digits
        url=source_url,
        snippet=snippet,
        title=title,
        display_domain="example.com",
    )


def mock_true_claim() -> FinalOutput:
    """Mock response for a true claim."""
    ev1 = create_evidence_item(
        "https://www.nasa.gov/earth", "NASA satellite imagery confirms Earth is an oblate spheroid."
    )
    ev2 = create_evidence_item(
        "https://www.nationalgeographic.com/science/article/earth",
        "Geodetic surveys have repeatedly measured Earth's curvature.",
    )

    return FinalOutput(
        answer="Scientific consensus and direct observation confirm Earth is round.",
        citations=[
            Citation(evidence_id=ev1.id, url=ev1.url),
            Citation(evidence_id=ev2.id, url=ev2.url),
        ],
        confidence=0.98,
        notes="Multiple reliable sources including space agencies and geodetic surveys confirm this.",
    )


def mock_false_claim() -> FinalOutput:
    """Mock response for a false claim."""
    ev1 = create_evidence_item(
        "https://www.cdc.gov/vaccines/facts", "Extensive studies show vaccines do not cause autism."
    )

    return FinalOutput(
        answer="The claim is thoroughly debunked by medical consensus. The original study linking vaccines to autism was retracted.",
        citations=[Citation(evidence_id=ev1.id, url=ev1.url)],
        confidence=0.95,
        notes="Extensive studies show vaccines do not cause autism.",
    )


def mock_uncertain_claim() -> FinalOutput:
    """Mock response for an uncertain claim."""
    return FinalOutput(
        answer="There is conflicting evidence regarding this specific detail.",
        citations=[],
        confidence=0.4,
        notes="Data is from 2020. Recent studies from 2024 are missing.",
    )


def get_mock_response(trigger: str) -> FinalOutput:
    """Factory to return specific mock responses based on trigger string."""
    trigger = trigger.lower()
    if "mock:true" in trigger:
        return mock_true_claim()
    elif "mock:false" in trigger:
        return mock_false_claim()
    elif "mock:uncertain" in trigger:
        return mock_uncertain_claim()
    else:
        # Default fallback (acts effectively as 'mock:true' for generic testing)
        return mock_true_claim()
