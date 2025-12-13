"""graph tests for the Fact Analyst node."""

from unittest.mock import patch

from pydantic import HttpUrl

from src.check_it_ai.graph.nodes.fact_analyst import (
    SourceCredibilityScorer,
    aggregate_verdicts,
    evaluate_single_pair,
    extract_claims,
    fact_analyst_node,
    synthesize_overall_verdict,
)
from src.check_it_ai.graph.state import AgentState
from src.check_it_ai.types.analyst import ExtractedClaims, SingleEvaluation
from src.check_it_ai.types.evidence import EvidenceVerdict, Finding
from src.check_it_ai.types.search import SearchResult


class TestSourceCredibilityScorer:
    """Test source credibility scoring logic."""

    def create_result(self, url: str, title: str = "Test Title") -> SearchResult:
        """Helper to create search result."""
        domain = url.split("//")[-1].split("/")[0]
        return SearchResult(
            title=title,
            snippet="Test snippet",
            url=HttpUrl(url),
            display_domain=domain,
            rank=1,
        )

    def test_fact_checker_score(self):
        """Test detection of fact checkers via title prefix."""
        res = self.create_result("https://snopes.com/fact-check", "[FACT-CHECK] Is the sky blue?")
        assert SourceCredibilityScorer.score(res) == SourceCredibilityScorer.SCORE_FACT_CHECKER

    def test_gov_edu_score(self):
        """Test .gov and .edu domains."""
        res_gov = self.create_result("https://nasa.gov/moon", "Moon landing")
        assert SourceCredibilityScorer.score(res_gov) == SourceCredibilityScorer.SCORE_GOV_EDU

        res_edu = self.create_result("https://mit.edu/research", "Research")
        assert SourceCredibilityScorer.score(res_edu) == SourceCredibilityScorer.SCORE_GOV_EDU

        res_uk_gov = self.create_result("https://www.service.gov.uk", "UK Service")
        assert SourceCredibilityScorer.score(res_uk_gov) == SourceCredibilityScorer.SCORE_GOV_EDU

    def test_news_org_score(self):
        """Test reputable news organizations."""
        res_bbc = self.create_result("https://www.bbc.com/news", "BBC News")
        assert SourceCredibilityScorer.score(res_bbc) == SourceCredibilityScorer.SCORE_NEWS_ORG

        res_reuters = self.create_result("https://reuters.com/wire", "Reuters")
        assert SourceCredibilityScorer.score(res_reuters) == SourceCredibilityScorer.SCORE_NEWS_ORG

    def test_generic_score(self):
        """Test generic web results."""
        res_blog = self.create_result("https://myrandomblog.com/post", "Blog Post")
        assert SourceCredibilityScorer.score(res_blog) == SourceCredibilityScorer.SCORE_GENERIC

    # Tests for normalized scores (0.0-1.0 floats for LLM prompts)
    def test_normalized_gov_edu(self):
        """Test normalized score for .gov/.edu domains."""
        res = self.create_result("https://nasa.gov/moon", "Moon landing")
        assert SourceCredibilityScorer.score_normalized(res) == 0.95

    def test_normalized_news(self):
        """Test normalized score for news domains."""
        res = self.create_result("https://www.bbc.com/news", "BBC News")
        assert SourceCredibilityScorer.score_normalized(res) == 0.70

    def test_normalized_generic(self):
        """Test normalized score for generic domains."""
        res = self.create_result("https://randomsite.com/page", "Random")
        assert SourceCredibilityScorer.score_normalized(res) == 0.50

    def test_normalized_fact_checker(self):
        """Test normalized score for fact-checker sources."""
        res = self.create_result("https://snopes.com/check", "[FACT-CHECK] Claim")
        assert SourceCredibilityScorer.score_normalized(res) == 0.95


class TestFactAnalystNode:
    """Test the full fact_analyst_node function."""

    def test_empty_results(self):
        """Test handling of empty search results."""
        state = AgentState(search_results=[])
        result = fact_analyst_node(state)

        bundle = result["evidence_bundle"]
        assert bundle.overall_verdict == EvidenceVerdict.INSUFFICIENT
        assert len(bundle.items) == 0

    @patch("src.check_it_ai.graph.nodes.fact_analyst.evaluate_single_pair")
    @patch("src.check_it_ai.graph.nodes.fact_analyst.extract_claims")
    def test_supported_verdict(self, mock_extract_claims, mock_evaluate):
        """Test supported verdict flow with new pipeline."""
        # Mock claim extraction to return single claim
        mock_extract_claims.return_value = ["The moon is made of rock"]

        # Mock per-pair evaluation to return SUPPORTED
        mock_evaluate.return_value = SingleEvaluation(
            verdict="SUPPORTED", confidence=0.9, reasoning="NASA confirms the moon is made of rock."
        )

        # Create high quality results
        results = [
            SearchResult(
                title="NASA confirms",
                snippet="The moon is made of rock.",
                url=HttpUrl("https://nasa.gov"),
                display_domain="nasa.gov",
                rank=1,
            )
        ]
        state = AgentState(user_query="Is the moon made of rock?", search_results=results)
        result = fact_analyst_node(state)

        bundle = result["evidence_bundle"]
        assert bundle.overall_verdict == EvidenceVerdict.SUPPORTED
        assert len(bundle.items) == 1
        assert bundle.items[0].id == "E1"
        assert bundle.findings[0].verdict == EvidenceVerdict.SUPPORTED
        assert bundle.findings[0].claim == "The moon is made of rock"

    @patch("src.check_it_ai.graph.nodes.fact_analyst.evaluate_single_pair")
    @patch("src.check_it_ai.graph.nodes.fact_analyst.extract_claims")
    def test_multiple_claims_mixed_verdicts(self, mock_extract_claims, mock_evaluate):
        """Test pipeline with multiple claims having different verdicts."""
        # Mock claim extraction to return two claims
        mock_extract_claims.return_value = [
            "Einstein invented the light bulb",
            "Einstein won a Nobel Prize",
        ]

        # Mock evaluations: first claim NOT_SUPPORTED, second SUPPORTED
        mock_evaluate.side_effect = [
            # First claim evaluations (against 1 evidence item)
            SingleEvaluation(
                verdict="NOT_SUPPORTED", confidence=0.85, reasoning="Edison invented it"
            ),
            # Second claim evaluations
            SingleEvaluation(verdict="SUPPORTED", confidence=0.9, reasoning="Nobel Prize 1921"),
        ]

        results = [
            SearchResult(
                title="History of inventions",
                snippet="Thomas Edison invented the light bulb. Einstein won Nobel Prize in 1921.",
                url=HttpUrl("https://history.com"),
                display_domain="history.com",
                rank=1,
            )
        ]
        state = AgentState(
            user_query="Einstein invented the light bulb and won a Nobel Prize",
            search_results=results,
        )
        result = fact_analyst_node(state)

        bundle = result["evidence_bundle"]
        # Overall should be NOT_SUPPORTED (priority over SUPPORTED)
        assert bundle.overall_verdict == EvidenceVerdict.NOT_SUPPORTED
        assert len(bundle.findings) == 2
        assert bundle.findings[0].verdict == EvidenceVerdict.NOT_SUPPORTED
        assert bundle.findings[1].verdict == EvidenceVerdict.SUPPORTED

    @patch("src.check_it_ai.graph.nodes.fact_analyst.evaluate_single_pair")
    @patch("src.check_it_ai.graph.nodes.fact_analyst.extract_claims")
    def test_contested_verdict_detection(self, mock_extract_claims, mock_evaluate):
        """Test that conflicting evidence within same claim produces CONTESTED."""
        mock_extract_claims.return_value = ["The sky is blue"]

        # Two evidence items with conflicting verdicts for same claim
        mock_evaluate.side_effect = [
            SingleEvaluation(verdict="SUPPORTED", confidence=0.9, reasoning="..."),
            SingleEvaluation(verdict="NOT_SUPPORTED", confidence=0.8, reasoning="..."),
        ]

        results = [
            SearchResult(
                title="Source 1",
                snippet="Sky is blue",
                url=HttpUrl("https://a.com"),
                display_domain="a.com",
                rank=1,
            ),
            SearchResult(
                title="Source 2",
                snippet="Sky is not blue",
                url=HttpUrl("https://b.com"),
                display_domain="b.com",
                rank=2,
            ),
        ]
        state = AgentState(user_query="The sky is blue", search_results=results)
        result = fact_analyst_node(state)

        bundle = result["evidence_bundle"]
        assert bundle.overall_verdict == EvidenceVerdict.CONTESTED
        assert bundle.findings[0].verdict == EvidenceVerdict.CONTESTED


class TestClaimExtraction:
    """Test the extract_claims function."""

    @patch("src.check_it_ai.graph.nodes.fact_analyst.ChatPromptTemplate")
    @patch("src.check_it_ai.graph.nodes.fact_analyst.get_analyst_llm")
    def test_extract_single_claim(self, mock_get_llm, mock_prompt_template):
        """Test extraction of a single atomic claim."""
        # Setup mock chain
        mock_chain = mock_prompt_template.from_messages.return_value.__or__.return_value
        mock_chain.invoke.return_value = ExtractedClaims(claims=["The Earth is round"])

        result = extract_claims("Is the Earth round?")

        assert result == ["The Earth is round"]
        mock_get_llm.assert_called_once()

    @patch("src.check_it_ai.graph.nodes.fact_analyst.ChatPromptTemplate")
    @patch("src.check_it_ai.graph.nodes.fact_analyst.get_analyst_llm")
    def test_extract_multiple_claims(self, mock_get_llm, mock_prompt_template):
        """Test extraction of multiple claims from compound query."""
        mock_chain = mock_prompt_template.from_messages.return_value.__or__.return_value
        mock_chain.invoke.return_value = ExtractedClaims(
            claims=["Einstein invented the light bulb", "Einstein won a Nobel Prize"]
        )

        result = extract_claims("Did Einstein invent the light bulb and win a Nobel Prize?")

        assert len(result) == 2
        assert "Einstein invented the light bulb" in result
        assert "Einstein won a Nobel Prize" in result

    @patch("src.check_it_ai.graph.nodes.fact_analyst.get_analyst_llm")
    def test_extract_claims_fallback_on_error(self, mock_get_llm):
        """Test fallback to original query when LLM fails."""
        mock_get_llm.side_effect = Exception("LLM unavailable")

        result = extract_claims("Some claim to verify")

        assert result == ["Some claim to verify"]

    @patch("src.check_it_ai.graph.nodes.fact_analyst.ChatPromptTemplate")
    @patch("src.check_it_ai.graph.nodes.fact_analyst.get_analyst_llm")
    def test_extract_claims_max_five(self, mock_get_llm, mock_prompt_template):
        """Test that extraction respects max 5 claims limit."""
        mock_chain = mock_prompt_template.from_messages.return_value.__or__.return_value
        mock_chain.invoke.return_value = ExtractedClaims(
            claims=["Claim 1", "Claim 2", "Claim 3", "Claim 4", "Claim 5"]
        )

        result = extract_claims("Complex query with many facts")

        assert len(result) <= 5


class TestEvaluateSinglePair:
    """Test the evaluate_single_pair function."""

    @patch("src.check_it_ai.graph.nodes.fact_analyst.ChatPromptTemplate")
    @patch("src.check_it_ai.graph.nodes.fact_analyst.get_analyst_llm")
    def test_evaluate_supported(self, mock_get_llm, mock_prompt_template):
        """Test evaluation that returns SUPPORTED verdict."""
        mock_chain = mock_prompt_template.from_messages.return_value.__or__.return_value
        mock_chain.invoke.return_value = SingleEvaluation(
            verdict="SUPPORTED", confidence=0.9, reasoning="The snippet confirms the claim."
        )

        result = evaluate_single_pair(
            claim="The Earth is round",
            snippet="Scientific evidence shows Earth is spherical.",
            credibility=0.95,
        )

        assert result.verdict == "SUPPORTED"
        assert result.confidence == 0.9

    @patch("src.check_it_ai.graph.nodes.fact_analyst.ChatPromptTemplate")
    @patch("src.check_it_ai.graph.nodes.fact_analyst.get_analyst_llm")
    def test_evaluate_not_supported(self, mock_get_llm, mock_prompt_template):
        """Test evaluation that returns NOT_SUPPORTED verdict."""
        mock_chain = mock_prompt_template.from_messages.return_value.__or__.return_value
        mock_chain.invoke.return_value = SingleEvaluation(
            verdict="NOT_SUPPORTED", confidence=0.85, reasoning="The snippet contradicts the claim."
        )

        result = evaluate_single_pair(
            claim="The sky is green",
            snippet="The sky appears blue due to light scattering.",
            credibility=0.70,
        )

        assert result.verdict == "NOT_SUPPORTED"
        assert result.confidence == 0.85

    @patch("src.check_it_ai.graph.nodes.fact_analyst.get_analyst_llm")
    def test_evaluate_fallback_on_error(self, mock_get_llm):
        """Test fallback when LLM fails."""
        mock_get_llm.side_effect = Exception("LLM unavailable")

        result = evaluate_single_pair(claim="Some claim", snippet="Some snippet", credibility=0.5)

        assert result.verdict == "IRRELEVANT"
        assert result.confidence == 0.5
        assert "error" in result.reasoning.lower()


class TestVerdictAggregation:
    """Test verdict aggregation logic."""

    def test_all_supported(self):
        """All SUPPORTED → SUPPORTED."""
        evals = [
            ("E1", SingleEvaluation(verdict="SUPPORTED", confidence=0.9, reasoning="...")),
            ("E2", SingleEvaluation(verdict="SUPPORTED", confidence=0.8, reasoning="...")),
        ]
        verdict, ids = aggregate_verdicts(evals)
        assert verdict == EvidenceVerdict.SUPPORTED
        assert ids == ["E1", "E2"]

    def test_all_not_supported(self):
        """All NOT_SUPPORTED → NOT_SUPPORTED."""
        evals = [
            ("E1", SingleEvaluation(verdict="NOT_SUPPORTED", confidence=0.9, reasoning="...")),
            ("E2", SingleEvaluation(verdict="NOT_SUPPORTED", confidence=0.8, reasoning="...")),
        ]
        verdict, ids = aggregate_verdicts(evals)
        assert verdict == EvidenceVerdict.NOT_SUPPORTED
        assert ids == ["E1", "E2"]

    def test_conflict_detection(self):
        """Mixed verdicts → CONTESTED."""
        evals = [
            ("E1", SingleEvaluation(verdict="SUPPORTED", confidence=0.9, reasoning="...")),
            ("E2", SingleEvaluation(verdict="NOT_SUPPORTED", confidence=0.8, reasoning="...")),
        ]
        verdict, ids = aggregate_verdicts(evals)
        assert verdict == EvidenceVerdict.CONTESTED
        assert "E1" in ids
        assert "E2" in ids

    def test_all_irrelevant(self):
        """All IRRELEVANT → INSUFFICIENT."""
        evals = [
            ("E1", SingleEvaluation(verdict="IRRELEVANT", confidence=0.5, reasoning="...")),
            ("E2", SingleEvaluation(verdict="IRRELEVANT", confidence=0.5, reasoning="...")),
        ]
        verdict, ids = aggregate_verdicts(evals)
        assert verdict == EvidenceVerdict.INSUFFICIENT
        assert ids == []

    def test_supported_with_irrelevant(self):
        """SUPPORTED + IRRELEVANT → SUPPORTED (irrelevant ignored)."""
        evals = [
            ("E1", SingleEvaluation(verdict="SUPPORTED", confidence=0.9, reasoning="...")),
            ("E2", SingleEvaluation(verdict="IRRELEVANT", confidence=0.5, reasoning="...")),
        ]
        verdict, ids = aggregate_verdicts(evals)
        assert verdict == EvidenceVerdict.SUPPORTED
        assert ids == ["E1"]

    def test_empty_evaluations(self):
        """Empty list → INSUFFICIENT."""
        verdict, ids = aggregate_verdicts([])
        assert verdict == EvidenceVerdict.INSUFFICIENT
        assert ids == []


class TestSynthesizeOverallVerdict:
    """Test overall verdict synthesis from findings."""

    def test_all_supported_findings(self):
        """All claims supported → SUPPORTED."""
        findings = [
            Finding(claim="Claim 1", verdict=EvidenceVerdict.SUPPORTED, evidence_ids=["E1"]),
            Finding(claim="Claim 2", verdict=EvidenceVerdict.SUPPORTED, evidence_ids=["E2"]),
        ]
        assert synthesize_overall_verdict(findings) == EvidenceVerdict.SUPPORTED

    def test_contested_takes_priority(self):
        """CONTESTED in any finding → CONTESTED overall."""
        findings = [
            Finding(claim="Claim 1", verdict=EvidenceVerdict.SUPPORTED, evidence_ids=["E1"]),
            Finding(claim="Claim 2", verdict=EvidenceVerdict.CONTESTED, evidence_ids=["E2", "E3"]),
        ]
        assert synthesize_overall_verdict(findings) == EvidenceVerdict.CONTESTED

    def test_not_supported_over_supported(self):
        """NOT_SUPPORTED + SUPPORTED → NOT_SUPPORTED."""
        findings = [
            Finding(claim="Claim 1", verdict=EvidenceVerdict.SUPPORTED, evidence_ids=["E1"]),
            Finding(claim="Claim 2", verdict=EvidenceVerdict.NOT_SUPPORTED, evidence_ids=["E2"]),
        ]
        assert synthesize_overall_verdict(findings) == EvidenceVerdict.NOT_SUPPORTED

    def test_insufficient_when_mixed_with_supported(self):
        """SUPPORTED + INSUFFICIENT → INSUFFICIENT."""
        findings = [
            Finding(claim="Claim 1", verdict=EvidenceVerdict.SUPPORTED, evidence_ids=["E1"]),
            Finding(claim="Claim 2", verdict=EvidenceVerdict.INSUFFICIENT, evidence_ids=[]),
        ]
        assert synthesize_overall_verdict(findings) == EvidenceVerdict.INSUFFICIENT

    def test_empty_findings(self):
        """Empty findings → INSUFFICIENT."""
        assert synthesize_overall_verdict([]) == EvidenceVerdict.INSUFFICIENT
