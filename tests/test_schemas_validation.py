"""Unit tests for Pydantic schema validation."""

import pytest
from pydantic import ValidationError

from src.check_it_ai.types.schemas import (
    Citation,
    EvidenceBundle,
    EvidenceItem,
    FinalOutput,
    Finding,
    SearchQuery,
    SearchResult,
)


class TestSearchQuery:
    """Tests for SearchQuery schema."""

    def test_valid_search_query(self):
        """Test valid search query creation."""
        query = SearchQuery(query="When did World War II end?")
        assert query.query == "When did World War II end?"
        assert query.max_results == 10  # default value

    def test_search_query_with_custom_max_results(self):
        """Test search query with custom max results."""
        query = SearchQuery(query="test", max_results=20)
        assert query.max_results == 20

    def test_search_query_empty_string_fails(self):
        """Test that empty query string fails validation."""
        with pytest.raises(ValidationError):
            SearchQuery(query="")


class TestSearchResult:
    """Tests for SearchResult schema."""

    def test_valid_search_result(self):
        """Test valid search result creation."""
        result = SearchResult(
            title="World War II - Wikipedia",
            snippet="World War II ended in 1945...",
            url="https://en.wikipedia.org/wiki/World_War_II",
            display_domain="en.wikipedia.org",
            rank=1,
        )
        assert result.title == "World War II - Wikipedia"
        assert result.rank == 1

    def test_invalid_url_fails(self):
        """Test that invalid URL fails validation."""
        with pytest.raises(ValidationError):
            SearchResult(
                title="Test",
                snippet="Test snippet",
                url="not-a-valid-url",
                display_domain="test.com",
                rank=1,
            )

    def test_rank_must_be_positive(self):
        """Test that rank must be >= 1."""
        with pytest.raises(ValidationError):
            SearchResult(
                title="Test",
                snippet="Test snippet",
                url="https://test.com",
                display_domain="test.com",
                rank=0,
            )


class TestEvidenceItem:
    """Tests for EvidenceItem schema."""

    def test_valid_evidence_item(self):
        """Test valid evidence item creation."""
        item = EvidenceItem(
            id="E1",
            title="Wikipedia Article",
            snippet="Historical fact...",
            url="https://wikipedia.org/article",
            display_domain="wikipedia.org",
        )
        assert item.id == "E1"

    def test_evidence_id_format_E1(self):
        """Test valid evidence ID format E1."""
        item = EvidenceItem(
            id="E1",
            title="Test",
            snippet="Test",
            url="https://test.com",
            display_domain="test.com",
        )
        assert item.id == "E1"

    def test_evidence_id_format_E123(self):
        """Test valid evidence ID format E123."""
        item = EvidenceItem(
            id="E123",
            title="Test",
            snippet="Test",
            url="https://test.com",
            display_domain="test.com",
        )
        assert item.id == "E123"

    def test_evidence_id_invalid_format_plain_number(self):
        """Test that plain number '1' fails validation."""
        with pytest.raises(ValidationError) as exc_info:
            EvidenceItem(
                id="1",
                title="Test",
                snippet="Test",
                url="https://test.com",
                display_domain="test.com",
            )
        assert "Evidence ID must match pattern" in str(exc_info.value)

    def test_evidence_id_invalid_format_with_dash(self):
        """Test that 'E-1' format fails validation."""
        with pytest.raises(ValidationError) as exc_info:
            EvidenceItem(
                id="E-1",
                title="Test",
                snippet="Test",
                url="https://test.com",
                display_domain="test.com",
            )
        assert "Evidence ID must match pattern" in str(exc_info.value)

    def test_evidence_id_invalid_lowercase(self):
        """Test that lowercase 'e1' fails validation."""
        with pytest.raises(ValidationError):
            EvidenceItem(
                id="e1",
                title="Test",
                snippet="Test",
                url="https://test.com",
                display_domain="test.com",
            )

    def test_evidence_id_invalid_no_number(self):
        """Test that 'E' without number fails validation."""
        with pytest.raises(ValidationError):
            EvidenceItem(
                id="E",
                title="Test",
                snippet="Test",
                url="https://test.com",
                display_domain="test.com",
            )


class TestFinding:
    """Tests for Finding schema."""

    def test_valid_finding(self):
        """Test valid finding creation."""
        finding = Finding(
            claim="World War II ended in 1945",
            verdict="supported",
            evidence_ids=["E1", "E2"],
        )
        assert finding.claim == "World War II ended in 1945"
        assert finding.verdict == "supported"
        assert len(finding.evidence_ids) == 2

    def test_finding_invalid_evidence_id(self):
        """Test that invalid evidence ID in list fails validation."""
        with pytest.raises(ValidationError) as exc_info:
            Finding(
                claim="Test claim",
                verdict="supported",
                evidence_ids=["E1", "2", "E3"],  # "2" is invalid
            )
        assert "Evidence ID must match pattern" in str(exc_info.value)

    def test_finding_empty_evidence_list(self):
        """Test finding with empty evidence list is valid."""
        finding = Finding(
            claim="Test claim",
            verdict="insufficient",
        )
        assert finding.evidence_ids == []


class TestEvidenceBundle:
    """Tests for EvidenceBundle schema."""

    def test_valid_evidence_bundle(self):
        """Test valid evidence bundle creation."""
        items = [
            EvidenceItem(
                id="E1",
                title="Test",
                snippet="Test",
                url="https://test.com",
                display_domain="test.com",
            )
        ]
        findings = [
            Finding(claim="Test claim", verdict="supported", evidence_ids=["E1"])
        ]
        bundle = EvidenceBundle(
            items=items, findings=findings, overall_verdict="supported"
        )
        assert bundle.overall_verdict == "supported"
        assert len(bundle.items) == 1
        assert len(bundle.findings) == 1

    def test_evidence_bundle_default_verdict(self):
        """Test evidence bundle defaults to 'insufficient'."""
        bundle = EvidenceBundle()
        assert bundle.overall_verdict == "insufficient"


class TestCitation:
    """Tests for Citation schema."""

    def test_valid_citation(self):
        """Test valid citation creation."""
        citation = Citation(evidence_id="E1", url="https://wikipedia.org")
        assert citation.evidence_id == "E1"

    def test_citation_invalid_evidence_id(self):
        """Test that invalid evidence ID fails validation."""
        with pytest.raises(ValidationError):
            Citation(evidence_id="1", url="https://test.com")

    def test_citation_invalid_url(self):
        """Test that invalid URL fails validation."""
        with pytest.raises(ValidationError):
            Citation(evidence_id="E1", url="not-a-url")


class TestFinalOutput:
    """Tests for FinalOutput schema."""

    def test_valid_final_output(self):
        """Test valid final output creation."""
        output = FinalOutput(
            answer="World War II ended in 1945",
            citations=[Citation(evidence_id="E1", url="https://wikipedia.org")],
            confidence=0.95,
            notes="High confidence based on multiple sources",
        )
        assert output.confidence == 0.95
        assert len(output.citations) == 1

    def test_confidence_range_valid_zero(self):
        """Test that confidence 0.0 is valid."""
        output = FinalOutput(answer="Test", confidence=0.0)
        assert output.confidence == 0.0

    def test_confidence_range_valid_one(self):
        """Test that confidence 1.0 is valid."""
        output = FinalOutput(answer="Test", confidence=1.0)
        assert output.confidence == 1.0

    def test_confidence_range_invalid_negative(self):
        """Test that negative confidence fails validation."""
        with pytest.raises(ValidationError):
            FinalOutput(answer="Test", confidence=-0.1)

    def test_confidence_range_invalid_above_one(self):
        """Test that confidence > 1.0 fails validation."""
        with pytest.raises(ValidationError) as exc_info:
            FinalOutput(answer="Test", confidence=1.5)
        assert "less than or equal to 1" in str(exc_info.value)

    def test_confidence_range_invalid_two(self):
        """Test that confidence of 2.0 fails validation."""
        with pytest.raises(ValidationError):
            FinalOutput(answer="Test", confidence=2.0)

    def test_final_output_default_notes(self):
        """Test that notes defaults to empty string."""
        output = FinalOutput(answer="Test", confidence=0.5)
        assert output.notes == ""
