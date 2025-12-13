"""Unit tests for the Fact Analyst node."""



from unittest.mock import patch

from pydantic import HttpUrl

from check_it_ai.graph.nodes.fact_analyst import (
    SourceCredibilityScorer,
    analyze_facts,
)
from check_it_ai.graph.state import AgentState
from check_it_ai.types.schemas import SearchResult


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


class TestFactAnalystNode:
    """Test the full analyze_facts node function."""

    def test_empty_results(self):
        """Test handling of empty search results."""
        state = AgentState(search_results=[])
        result = analyze_facts(state)

        bundle = result["evidence_bundle"]
        assert bundle.overall_verdict == "insufficient"
        assert len(bundle.items) == 0

    @patch("check_it_ai.graph.nodes.fact_analyst.ContentAnalyzer.determine_verdict")
    def test_supported_verdict(self, mock_determine_verdict):
        """Test supported verdict flow."""
        # Mock the verdict since we are testing the node orchestration, not the LLM
        mock_determine_verdict.return_value = "supported"

        # Create high quality results
        results = [
            SearchResult(
                title="NASA confirms",
                snippet="The moon is made of rock.",
                url=HttpUrl("https://nasa.gov"),
                display_domain="nasa.gov",
                rank=1
            )
        ]
        state = AgentState(user_query="Is the moon made of rock?", search_results=results)
        result = analyze_facts(state)

        bundle = result["evidence_bundle"]
        assert bundle.overall_verdict == "supported"
        assert len(bundle.items) == 1
        assert bundle.items[0].id == "E1"
        assert bundle.findings[0].verdict == "supported"


