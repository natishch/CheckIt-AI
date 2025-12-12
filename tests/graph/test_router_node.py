from src.check_it_ai.graph.nodes.router import router_node
from src.check_it_ai.graph.state import AgentState


class TestRouterNode:
    def test_empty_query_routes_to_clarify(self):
        state = AgentState(user_query="   ")
        new_state = router_node(state)

        assert new_state.route == "clarify"
        meta = new_state.run_metadata["router"]
        assert meta["trigger"] == "empty_query"
        assert meta["decision"] == "clarify"

    def test_underspecified_query_routes_to_clarify(self):
        state = AgentState(user_query="is it true?")
        new_state = router_node(state)

        assert new_state.route == "clarify"
        meta = new_state.run_metadata["router"]
        assert meta["trigger"] == "underspecified_query"
        assert meta["decision"] == "clarify"

    def test_non_historical_intent_routes_to_out_of_scope(self):
        state = AgentState(user_query="write me a poem about WW2")
        new_state = router_node(state)

        assert new_state.route == "out_of_scope"
        meta = new_state.run_metadata["router"]
        assert meta["trigger"] == "non_historical_intent"
        assert meta["decision"] == "out_of_scope"

    def test_default_routes_to_fact_check(self):
        state = AgentState(user_query="When did the Berlin Wall fall?")
        new_state = router_node(state)

        assert new_state.route == "fact_check"
        meta = new_state.run_metadata["router"]
        assert meta["trigger"] in ["default_fact_check", "explicit_verification"]
        assert meta["decision"] == "fact_check"
        assert meta["features"]["starts_like_question"] is True

    def test_ambiguous_reference_routes_to_clarify(self):
        # Contains a vague "this" without verification keywords - should trigger ambiguous_reference
        # Note: "Did this really happen?" matches verification patterns, so use different query
        state = AgentState(user_query="Tell me about this event")
        new_state = router_node(state)

        assert new_state.route == "clarify"
        meta = new_state.run_metadata["router"]
        assert meta["trigger"] == "ambiguous_reference"
        assert meta["decision"] == "clarify"

    def test_coding_request_routes_to_out_of_scope_with_intent_type(self):
        # Clearly a coding / implementation request, not historical fact-checking
        state = AgentState(user_query="Write a Python script that prints prime numbers")
        new_state = router_node(state)

        assert new_state.route == "out_of_scope"
        meta = new_state.run_metadata["router"]

        # Check trigger and decision (new Pydantic model fields)
        assert meta["trigger"] == "non_historical_intent"
        assert meta["decision"] == "out_of_scope"

        # More fine-grained category for debugging / UI
        assert meta.get("intent_type") == "coding_request"

    def test_chat_request_routes_to_out_of_scope_with_intent_type(self):
        # Generic chat / joke request, even if it mentions a historical entity
        state = AgentState(user_query="tell me a joke about Napoleon")
        new_state = router_node(state)

        assert new_state.route == "out_of_scope"
        meta = new_state.run_metadata["router"]

        assert meta["trigger"] == "non_historical_intent"
        assert meta["decision"] == "out_of_scope"
        assert meta.get("intent_type") == "chat_request"

    def test_fact_check_metadata_contains_features(self):
        # Historical question with enough detail should go to fact_check
        q = "When did the Berlin Wall fall?"
        state = AgentState(user_query=q)
        new_state = router_node(state)

        assert new_state.route == "fact_check"
        meta = new_state.run_metadata["router"]

        # Features dict should exist and contain some basic keys
        features = meta.get("features")
        assert isinstance(features, dict)
        assert "num_tokens" in features
        assert "num_chars" in features
        assert "starts_like_question" in features

        # Original query should be preserved
        assert new_state.user_query == q

    def test_hebrew_language_detection(self):
        """Test that Hebrew queries are detected correctly."""
        # Hebrew query: "Did World War II happen?" (in Hebrew)
        hebrew_query = "האם מלחמת העולם השנייה התרחשה?"
        state = AgentState(user_query=hebrew_query)
        new_state = router_node(state)

        meta = new_state.run_metadata["router"]
        # Should detect Hebrew language
        assert meta["detected_language"] == "he"
        # Should still route to fact_check (sufficient length)
        assert new_state.route == "fact_check"
        assert meta["decision"] == "fact_check"

    def test_explicit_verification_question_high_confidence(self):
        """Test that explicit verification questions get high confidence."""
        verification_query = "Is it true that World War II ended in 1945?"
        state = AgentState(user_query=verification_query)
        new_state = router_node(state)

        meta = new_state.run_metadata["router"]
        # Should trigger explicit verification
        assert meta["trigger"] == "explicit_verification"
        assert meta["decision"] == "fact_check"
        # Should have high confidence (verification + year + entity)
        assert meta["confidence"] >= 0.85
        # Should detect historical markers
        assert meta["has_historical_markers"] is True

    def test_confidence_scoring_with_historical_markers(self):
        """Test confidence scoring based on historical signals."""
        # Query with year and entity but no verification pattern
        query_with_markers = "When did Napoleon die in 1821?"
        state = AgentState(user_query=query_with_markers)
        new_state = router_node(state)

        meta = new_state.run_metadata["router"]
        assert meta["decision"] == "fact_check"
        # Should have medium-high confidence (year + entity + question)
        assert 0.65 <= meta["confidence"] <= 0.85
        assert meta["has_historical_markers"] is True

    def test_confidence_scoring_weak_signals(self):
        """Test confidence scoring with weak historical signals."""
        # Generic query without strong signals
        weak_query = "Tell me something"
        state = AgentState(user_query=weak_query)
        new_state = router_node(state)

        meta = new_state.run_metadata["router"]
        assert meta["decision"] == "fact_check"
        # Should have low confidence (base score only)
        assert meta["confidence"] <= 0.5
        assert meta["has_historical_markers"] is False

    def test_english_language_detection(self):
        """Test that English queries are detected correctly."""
        english_query = "When did the American Revolution begin?"
        state = AgentState(user_query=english_query)
        new_state = router_node(state)

        meta = new_state.run_metadata["router"]
        # Should detect English language
        assert meta["detected_language"] == "en"
        assert meta["decision"] == "fact_check"

    def test_confidence_included_in_all_routes(self):
        """Test that confidence field is present in all routing decisions."""
        test_cases = [
            ("   ", "clarify"),  # Empty
            ("write code", "out_of_scope"),  # Coding
            ("When did WWII end?", "fact_check"),  # Fact-check
        ]

        for query, expected_route in test_cases:
            state = AgentState(user_query=query)
            new_state = router_node(state)
            meta = new_state.run_metadata["router"]

            assert new_state.route == expected_route
            # Confidence should always be present
            assert "confidence" in meta
            assert isinstance(meta["confidence"], (int, float))
            assert 0.0 <= meta["confidence"] <= 1.0
