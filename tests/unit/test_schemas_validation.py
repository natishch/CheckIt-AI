"""Unit tests for Pydantic schema validation."""

import pytest
from pydantic import ValidationError

from src.check_it_ai.types.schemas import (
    Citation,
    EvidenceBundle,
    EvidenceItem,
    FinalOutput,
    Finding,
    RouterDecision,
    RouterMetadata,
    RouterTrigger,
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
        findings = [Finding(claim="Test claim", verdict="supported", evidence_ids=["E1"])]
        bundle = EvidenceBundle(items=items, findings=findings, overall_verdict="supported")
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


class TestRouterTrigger:
    """Tests for RouterTrigger StrEnum."""

    def test_router_trigger_string_values(self):
        """Test RouterTrigger enum values are strings."""
        assert RouterTrigger.EMPTY_QUERY == "empty_query"
        assert RouterTrigger.DEFAULT_FACT_CHECK == "default_fact_check"
        assert RouterTrigger.UNDERSPECIFIED_QUERY == "underspecified_query"

    def test_router_trigger_string_comparison(self):
        """Test StrEnum allows direct string comparison."""
        trigger = RouterTrigger.EMPTY_QUERY
        assert trigger == "empty_query"
        assert "empty_query" == trigger

    def test_router_trigger_all_clarification_triggers_exist(self):
        """Test all clarification trigger types exist."""
        clarification_triggers = [
            RouterTrigger.EMPTY_QUERY,
            RouterTrigger.TOO_SHORT,
            RouterTrigger.UNDERSPECIFIED_QUERY,
            RouterTrigger.UNRESOLVED_PRONOUN,
            RouterTrigger.AMBIGUOUS_REFERENCE,
            RouterTrigger.OVERLY_BROAD,
            RouterTrigger.UNSUPPORTED_LANGUAGE,
        ]
        assert len(clarification_triggers) == 7

    def test_router_trigger_all_out_of_scope_triggers_exist(self):
        """Test all out-of-scope trigger types exist."""
        out_of_scope_triggers = [
            RouterTrigger.CREATIVE_WRITING,
            RouterTrigger.CODING_REQUEST,
            RouterTrigger.CHAT_REQUEST,
            RouterTrigger.FUTURE_PREDICTION,
            RouterTrigger.CURRENT_EVENTS,
            RouterTrigger.OPINION_REQUEST,
            RouterTrigger.NON_HISTORICAL_INTENT,
        ]
        assert len(out_of_scope_triggers) == 7

    def test_router_trigger_fact_check_triggers_exist(self):
        """Test fact-check trigger types exist."""
        fact_check_triggers = [
            RouterTrigger.DEFAULT_FACT_CHECK,
            RouterTrigger.EXPLICIT_VERIFICATION,
        ]
        assert len(fact_check_triggers) == 2


class TestRouterDecision:
    """Tests for RouterDecision StrEnum."""

    def test_router_decision_all_values(self):
        """Test all three routing decisions exist."""
        assert RouterDecision.FACT_CHECK == "fact_check"
        assert RouterDecision.CLARIFY == "clarify"
        assert RouterDecision.OUT_OF_SCOPE == "out_of_scope"

    def test_router_decision_string_comparison(self):
        """Test StrEnum allows direct string comparison."""
        decision = RouterDecision.FACT_CHECK
        assert decision == "fact_check"
        assert "fact_check" == decision

    def test_router_decision_count(self):
        """Test that we have exactly 3 routing decisions."""
        decisions = list(RouterDecision)
        assert len(decisions) == 3


class TestRouterMetadata:
    """Tests for RouterMetadata schema."""

    def test_valid_router_metadata_minimal(self):
        """Test valid RouterMetadata creation with minimal fields."""
        metadata = RouterMetadata(
            trigger=RouterTrigger.DEFAULT_FACT_CHECK,
            decision=RouterDecision.FACT_CHECK,
            reasoning="Clear historical question",
            confidence=0.85,
            query_length_words=5,
        )
        assert metadata.trigger == RouterTrigger.DEFAULT_FACT_CHECK
        assert metadata.decision == RouterDecision.FACT_CHECK
        assert metadata.confidence == 0.85
        assert metadata.query_length_words == 5
        assert metadata.detected_language == "en"  # default
        assert metadata.has_historical_markers is False  # default
        assert metadata.matched_patterns == []  # default
        assert metadata.features == {}  # default
        assert metadata.intent_type is None  # default

    def test_valid_router_metadata_full(self):
        """Test valid RouterMetadata creation with all fields."""
        metadata = RouterMetadata(
            trigger=RouterTrigger.EXPLICIT_VERIFICATION,
            decision=RouterDecision.FACT_CHECK,
            reasoning="User asked to verify a claim",
            confidence=0.95,
            matched_patterns=["is it true", "verify"],
            query_length_words=8,
            has_historical_markers=True,
            detected_language="he",
            features={"has_question_mark": True, "word_count": 8},
            intent_type="verification",
        )
        assert metadata.confidence == 0.95
        assert metadata.detected_language == "he"
        assert metadata.has_historical_markers is True
        assert len(metadata.matched_patterns) == 2
        assert metadata.features["word_count"] == 8
        assert metadata.intent_type == "verification"

    def test_confidence_range_valid_boundaries(self):
        """Test that confidence 0.0 and 1.0 are valid."""
        metadata_zero = RouterMetadata(
            trigger=RouterTrigger.EMPTY_QUERY,
            decision=RouterDecision.CLARIFY,
            reasoning="Empty query",
            confidence=0.0,
            query_length_words=0,
        )
        assert metadata_zero.confidence == 0.0

        metadata_one = RouterMetadata(
            trigger=RouterTrigger.EXPLICIT_VERIFICATION,
            decision=RouterDecision.FACT_CHECK,
            reasoning="Explicit verification",
            confidence=1.0,
            query_length_words=10,
        )
        assert metadata_one.confidence == 1.0

    def test_confidence_range_invalid_negative(self):
        """Test that negative confidence fails validation."""
        with pytest.raises(ValidationError):
            RouterMetadata(
                trigger=RouterTrigger.DEFAULT_FACT_CHECK,
                decision=RouterDecision.FACT_CHECK,
                reasoning="Test",
                confidence=-0.1,
                query_length_words=5,
            )

    def test_confidence_range_invalid_above_one(self):
        """Test that confidence > 1.0 fails validation."""
        with pytest.raises(ValidationError):
            RouterMetadata(
                trigger=RouterTrigger.DEFAULT_FACT_CHECK,
                decision=RouterDecision.FACT_CHECK,
                reasoning="Test",
                confidence=1.5,
                query_length_words=5,
            )

    def test_detected_language_valid_hebrew(self):
        """Test valid Hebrew language code."""
        metadata = RouterMetadata(
            trigger=RouterTrigger.DEFAULT_FACT_CHECK,
            decision=RouterDecision.FACT_CHECK,
            reasoning="Test",
            confidence=0.5,
            query_length_words=5,
            detected_language="he",
        )
        assert metadata.detected_language == "he"

    def test_detected_language_valid_english(self):
        """Test valid English language code."""
        metadata = RouterMetadata(
            trigger=RouterTrigger.DEFAULT_FACT_CHECK,
            decision=RouterDecision.FACT_CHECK,
            reasoning="Test",
            confidence=0.5,
            query_length_words=5,
            detected_language="en",
        )
        assert metadata.detected_language == "en"

    def test_detected_language_invalid_other(self):
        """Test that non-Hebrew/English language code fails validation."""
        with pytest.raises(ValidationError) as exc_info:
            RouterMetadata(
                trigger=RouterTrigger.DEFAULT_FACT_CHECK,
                decision=RouterDecision.FACT_CHECK,
                reasoning="Test",
                confidence=0.5,
                query_length_words=5,
                detected_language="fr",
            )
        assert "detected_language" in str(exc_info.value).lower()

    def test_query_length_words_must_be_non_negative(self):
        """Test that query_length_words must be >= 0."""
        with pytest.raises(ValidationError):
            RouterMetadata(
                trigger=RouterTrigger.DEFAULT_FACT_CHECK,
                decision=RouterDecision.FACT_CHECK,
                reasoning="Test",
                confidence=0.5,
                query_length_words=-1,
            )

    def test_query_length_words_zero_valid(self):
        """Test that query_length_words can be 0."""
        metadata = RouterMetadata(
            trigger=RouterTrigger.EMPTY_QUERY,
            decision=RouterDecision.CLARIFY,
            reasoning="Empty query",
            confidence=0.0,
            query_length_words=0,
        )
        assert metadata.query_length_words == 0

    def test_reasoning_cannot_be_empty(self):
        """Test that reasoning must have at least 1 character."""
        with pytest.raises(ValidationError):
            RouterMetadata(
                trigger=RouterTrigger.DEFAULT_FACT_CHECK,
                decision=RouterDecision.FACT_CHECK,
                reasoning="",
                confidence=0.5,
                query_length_words=5,
            )

    def test_matched_patterns_defaults_to_empty_list(self):
        """Test matched_patterns defaults to empty list."""
        metadata = RouterMetadata(
            trigger=RouterTrigger.DEFAULT_FACT_CHECK,
            decision=RouterDecision.FACT_CHECK,
            reasoning="Test",
            confidence=0.5,
            query_length_words=5,
        )
        assert metadata.matched_patterns == []
        assert isinstance(metadata.matched_patterns, list)

    def test_features_dict_backward_compatibility(self):
        """Test that features dict supports backward compatibility."""
        metadata = RouterMetadata(
            trigger=RouterTrigger.DEFAULT_FACT_CHECK,
            decision=RouterDecision.FACT_CHECK,
            reasoning="Test",
            confidence=0.5,
            query_length_words=5,
            features={
                "has_question_mark": True,
                "word_count": 5,
                "custom_field": "custom_value",
            },
        )
        assert metadata.features["has_question_mark"] is True
        assert metadata.features["word_count"] == 5
        assert metadata.features["custom_field"] == "custom_value"

    def test_intent_type_optional(self):
        """Test that intent_type is optional and can be None."""
        metadata = RouterMetadata(
            trigger=RouterTrigger.DEFAULT_FACT_CHECK,
            decision=RouterDecision.FACT_CHECK,
            reasoning="Test",
            confidence=0.5,
            query_length_words=5,
        )
        assert metadata.intent_type is None

        metadata_with_intent = RouterMetadata(
            trigger=RouterTrigger.CODING_REQUEST,
            decision=RouterDecision.OUT_OF_SCOPE,
            reasoning="Coding request detected",
            confidence=0.9,
            query_length_words=7,
            intent_type="coding",
        )
        assert metadata_with_intent.intent_type == "coding"
