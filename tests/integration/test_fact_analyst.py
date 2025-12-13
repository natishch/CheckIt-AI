"""Integration tests for Fact Analyst LLM capabilities (real API).

These tests use the real LLM API to verify the new fact analyst pipeline:
- Claim extraction
- Per-pair evidence evaluation
- Full pipeline verdict determination

Run with: uv run pytest tests/integration/test_fact_analyst.py -v -s -m integration
"""

import os

import pytest
from dotenv import load_dotenv
from pydantic import HttpUrl

from src.check_it_ai.config import settings
from src.check_it_ai.graph.nodes.fact_analyst import (
    ContentAnalyzer,
    evaluate_single_pair,
    extract_claims,
    fact_analyst_node,
)
from src.check_it_ai.graph.state import AgentState
from src.check_it_ai.llm.providers import check_provider_health
from src.check_it_ai.types.evidence import EvidenceItem, EvidenceVerdict
from src.check_it_ai.types.search import SearchResult

# Load environment variables
load_dotenv()


def _has_llm_available() -> bool:
    """Check if any LLM is available (cloud API or local)."""
    # Check cloud API keys
    has_cloud_key = bool(
        os.getenv("OPENAI_API_KEY")
        or os.getenv("ANTHROPIC_API_KEY")
        or os.getenv("GOOGLE_GENAI_API_KEY")
    )
    if has_cloud_key:
        return True

    # Check if local LLM is configured and healthy
    if settings.writer_llm_provider == "local":
        health = check_provider_health(settings)
        return health.get("healthy", False)

    return False


@pytest.mark.integration
class TestClaimExtractionLLM:
    """Integration tests for claim extraction with real LLM."""

    @pytest.fixture(autouse=True)
    def check_llm_available(self):
        """Skip if no LLM is available."""
        if not _has_llm_available():
            pytest.skip("No LLM available (configure cloud API key or local LLM)")

    def test_extract_single_atomic_claim(self):
        """Test extraction of a simple atomic claim."""
        query = "The Earth is round"
        claims = extract_claims(query)

        assert len(claims) >= 1
        assert len(claims) <= 5
        # Should preserve the core claim
        assert any("earth" in c.lower() and "round" in c.lower() for c in claims)

    def test_extract_compound_claims(self):
        """Test extraction of multiple claims from compound query."""
        query = "Einstein invented the light bulb and won a Nobel Prize"
        claims = extract_claims(query)

        assert len(claims) >= 2
        # Should split into separate claims
        has_light_bulb_claim = any("light bulb" in c.lower() for c in claims)
        has_nobel_claim = any("nobel" in c.lower() for c in claims)
        assert has_light_bulb_claim or has_nobel_claim

    def test_extract_verification_question(self):
        """Test extraction from verification-style question."""
        query = "Is it true that the Titanic sank in 1912?"
        claims = extract_claims(query)

        assert len(claims) >= 1
        # Should extract the factual claim(s) - may be split into multiple atomic claims
        claims_text = " ".join(claims).lower()
        assert "titanic" in claims_text
        assert "1912" in claims_text or "sank" in claims_text

    def test_extract_complex_historical_query(self):
        """Test extraction from complex historical query."""
        query = "Did Apple buy Twitter for $50 billion in 2023?"
        claims = extract_claims(query)

        # Should extract multiple atomic claims
        assert len(claims) >= 1
        # Could be split into: Apple bought Twitter, price was $50B, happened in 2023


@pytest.mark.integration
class TestEvaluateSinglePairLLM:
    """Integration tests for per-pair evaluation with real LLM."""

    @pytest.fixture(autouse=True)
    def check_llm_available(self):
        """Skip if no LLM is available."""
        if not _has_llm_available():
            pytest.skip("No LLM available (configure cloud API key or local LLM)")

    def test_evaluate_supported_claim(self):
        """Test evaluation of clearly supported claim."""
        claim = "World War II ended in 1945"
        snippet = "World War II ended on September 2, 1945, with the formal surrender of Japan."
        credibility = 0.95

        result = evaluate_single_pair(claim, snippet, credibility)

        assert result.verdict == "SUPPORTED"
        assert result.confidence >= 0.7
        assert len(result.reasoning) > 0

    def test_evaluate_refuted_claim(self):
        """Test evaluation of clearly refuted claim."""
        claim = "Einstein invented the light bulb"
        snippet = "Thomas Edison is credited with inventing the practical incandescent light bulb in 1879."
        credibility = 0.95

        result = evaluate_single_pair(claim, snippet, credibility)

        assert result.verdict == "NOT_SUPPORTED"
        assert len(result.reasoning) > 0

    def test_evaluate_irrelevant_snippet(self):
        """Test evaluation when snippet doesn't address claim."""
        claim = "The moon is made of cheese"
        snippet = "The stock market closed higher today on strong earnings reports."
        credibility = 0.70

        result = evaluate_single_pair(claim, snippet, credibility)

        assert result.verdict == "IRRELEVANT"

    def test_evaluate_with_low_credibility(self):
        """Test that low credibility affects confidence."""
        claim = "Napoleon died in 1821"
        snippet = "Napoleon Bonaparte died on May 5, 1821, on the island of Saint Helena."
        credibility = 0.30  # Low credibility source

        result = evaluate_single_pair(claim, snippet, credibility)

        # Should still recognize support but with lower confidence
        assert result.verdict == "SUPPORTED"
        # Confidence should be lower due to source credibility
        assert result.confidence <= 0.85


@pytest.mark.integration
class TestFactAnalystPipelineLLM:
    """Integration tests for the full fact analyst pipeline with real LLM."""

    @pytest.fixture(autouse=True)
    def check_llm_available(self):
        """Skip if no LLM is available."""
        if not _has_llm_available():
            pytest.skip("No LLM available (configure cloud API key or local LLM)")

    def _create_search_result(
        self, title: str, snippet: str, url: str, domain: str
    ) -> SearchResult:
        """Helper to create search result."""
        return SearchResult(
            title=title,
            snippet=snippet,
            url=HttpUrl(url),
            display_domain=domain,
            rank=1,
        )

    def test_pipeline_supported_verdict(self):
        """Test full pipeline with clearly supported claim."""
        results = [
            self._create_search_result(
                title="World War II - Wikipedia",
                snippet="World War II ended on September 2, 1945, with Japan's formal surrender.",
                url="https://en.wikipedia.org/wiki/World_War_II",
                domain="en.wikipedia.org",
            ),
            self._create_search_result(
                title="WWII History",
                snippet="The war in Europe ended on May 8, 1945 (V-E Day). Japan surrendered in September 1945.",
                url="https://history.com/wwii",
                domain="history.com",
            ),
        ]

        state = AgentState(
            user_query="When did World War II end?",
            search_results=results,
        )

        result = fact_analyst_node(state)
        bundle = result["evidence_bundle"]

        assert bundle.overall_verdict == EvidenceVerdict.SUPPORTED
        assert len(bundle.findings) >= 1
        assert len(bundle.items) == 2

    def test_pipeline_not_supported_verdict(self):
        """Test full pipeline with clearly refuted claim."""
        results = [
            self._create_search_result(
                title="Light Bulb History",
                snippet="Thomas Edison invented the practical incandescent light bulb in 1879.",
                url="https://britannica.com/light-bulb",
                domain="britannica.com",
            ),
            self._create_search_result(
                title="Edison Biography",
                snippet="Edison's most famous invention was the light bulb, not Einstein.",
                url="https://biography.com/edison",
                domain="biography.com",
            ),
        ]

        state = AgentState(
            user_query="Did Einstein invent the light bulb?",
            search_results=results,
        )

        result = fact_analyst_node(state)
        bundle = result["evidence_bundle"]

        assert bundle.overall_verdict == EvidenceVerdict.NOT_SUPPORTED
        assert len(bundle.findings) >= 1

    def test_pipeline_insufficient_verdict(self):
        """Test full pipeline when evidence doesn't address claim."""
        results = [
            self._create_search_result(
                title="Stock Market News",
                snippet="The stock market closed higher today.",
                url="https://finance.com/news",
                domain="finance.com",
            ),
        ]

        state = AgentState(
            user_query="Did Napoleon eat breakfast on his 30th birthday?",
            search_results=results,
        )

        result = fact_analyst_node(state)
        bundle = result["evidence_bundle"]

        # Evidence is irrelevant, so should be INSUFFICIENT
        assert bundle.overall_verdict == EvidenceVerdict.INSUFFICIENT

    def test_pipeline_metadata_populated(self):
        """Test that pipeline populates metadata correctly."""
        results = [
            self._create_search_result(
                title="Historical Facts",
                snippet="The Battle of Waterloo was fought on June 18, 1815.",
                url="https://history.gov/waterloo",
                domain="history.gov",
            ),
        ]

        state = AgentState(
            user_query="When was the Battle of Waterloo?",
            search_results=results,
        )

        result = fact_analyst_node(state)

        # Check metadata
        assert "run_metadata" in result
        assert "fact_analyst" in result["run_metadata"]
        metadata = result["run_metadata"]["fact_analyst"]

        assert "claims_extracted" in metadata
        assert "total_evidence_count" in metadata
        assert "findings_count" in metadata
        assert "overall_verdict" in metadata


# =============================================================================
# Legacy ContentAnalyzer Tests (preserved for backward compatibility)
# =============================================================================


@pytest.mark.integration
class TestContentAnalyzerLegacy:
    """Legacy integration tests for ContentAnalyzer.determine_verdict.

    These test the old approach which is still available for comparison.
    """

    @pytest.fixture(autouse=True)
    def check_llm_available(self):
        """Skip if no LLM is available."""
        if not _has_llm_available():
            pytest.skip("No LLM available (configure cloud API key or local LLM)")

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

        verdict = ContentAnalyzer.determine_verdict(evidence, [], query)
        assert verdict == "not_supported", f"Expected 'not_supported', got {verdict}"
