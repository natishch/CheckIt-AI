"""Integration tests for Fact Analyst LLM capabilities (real API).

These tests use the real OpenAI API to verify verdict determination.
"""

import os

import pytest
from dotenv import load_dotenv
from pydantic import HttpUrl

from check_it_ai.graph.nodes.fact_analyst import ContentAnalyzer
from check_it_ai.types.schemas import EvidenceItem

# Load environment variables
load_dotenv()

@pytest.mark.integration
class TestFactAnalystLLM:
    """Integration tests for ContentAnalyzer LLM functions."""

    @pytest.fixture(autouse=True)
    def check_api_key(self):
        """Skip if OPENAI_API_KEY is not set."""
        if not os.getenv("OPENAI_API_KEY"):
            pytest.skip("OPENAI_API_KEY not configured")

    def _create_evidence(self, snippets: list[str]) -> list[EvidenceItem]:
        """Helper to create evidence items from snippets."""
        items = []
        for i, snippet in enumerate(snippets, 1):
            items.append(EvidenceItem(
                id=f"E{i}",
                title=f"Source {i}",
                snippet=snippet,
                url=HttpUrl(f"http://example{i}.com/article"),
                display_domain=f"example{i}.com"
            ))
        return items

    def test_verdict_supported_conversational(self):
        """Scenario: Conversational historical claim - Supported."""
        query = "I heard the Titanic sank in 1912. Is that true?"
        snippets = [
            "The RMS Titanic sank in the North Atlantic Ocean on April 15, 1912.",
            "More than 1,500 people died when the Titanic sank in 1912."
        ]
        evidence = self._create_evidence(snippets)

        # Should be supported
        verdict = ContentAnalyzer.determine_verdict(evidence, [], query)
        assert verdict == "supported", f"Expected 'supported', got {verdict}"

    def test_verdict_refuted_conversational(self):
        """Scenario: Conversational historical claim - Refuted."""
        query = "Someone told me Napoleon died in battle at Waterloo. I think that's right."
        snippets = [
            "Napoleon was defeated at Waterloo but died in exile on Saint Helena in 1821.",
            "His death in 1821 on the island of St. Helena was likely due to stomach cancer."
        ]
        evidence = self._create_evidence(snippets)

        # Should be not_supported
        verdict = ContentAnalyzer.determine_verdict(evidence, [], query)
        assert verdict == "not_supported", f"Expected 'not_supported', got {verdict}"

    def test_verdict_contested_conversational(self):
        """Scenario: Conversational historical claim - Contested."""
        query = "I read that Nero definitely started the Great Fire of Rome."
        snippets = [
            "Some ancient historians blamed Emperor Nero for the fire.",
            "Tacitus reports that Nero was not in Rome at the time and organized relief efforts.",
            "The true cause remains debated among historians."
        ]
        evidence = self._create_evidence(snippets)

        # Should be contested
        verdict = ContentAnalyzer.determine_verdict(evidence, [], query)
        assert verdict == "contested", f"Expected 'contested', got {verdict}"

    def test_verdict_insufficient_conversational(self):
        """Scenario: Conversational historical claim - Insufficient Evidence."""
        query = "I bet the first settler in Paris ate eggs for breakfast on their 20th birthday."
        snippets = [
            "The Parisii tribe settled the area around 250 BC.",
            "Archaeological evidence shows they ate grains and meat."
        ]
        evidence = self._create_evidence(snippets)

        # Should be insufficient (too specific/unknowable from general evidence)
        verdict = ContentAnalyzer.determine_verdict(evidence, [], query)
        assert verdict == "insufficient", f"Expected 'insufficient', got {verdict}"

    def test_verdict_nuanced_myth_conversational(self):
        """Scenario: Conversational historical claim - Nuanced Myth."""
        query = "My teacher said George Washington really chopped down a cherry tree."
        snippets = [
            "The story of Washington chopping down a cherry tree is a myth invented by biographer Mason Locke Weems.",
            "There is no historical evidence that Washington chopped down a cherry tree."
        ]
        evidence = self._create_evidence(snippets)

        # Should be not_supported
        verdict = ContentAnalyzer.determine_verdict(evidence, [], query)
        assert verdict == "not_supported", f"Expected 'not_supported', got {verdict}"
