from src.check_it_ai.graph.state import AgentState
from src.check_it_ai.graph.nodes.router import router_node
from src.check_it_ai.types.writer import WriterOutput



class TestRouterNode:
    # -------------------------------------------------------------------------
    # Existing tests
    # -------------------------------------------------------------------------

    def test_empty_query_routes_to_clarify(self):
        state = AgentState(user_query="   ")
        new_state = router_node(state)

        assert new_state.route == "clarify"
        meta = new_state.run_metadata["router"]
        assert meta["reason_code"] == "empty_query"

    def test_underspecified_query_routes_to_clarify(self):
        state = AgentState(user_query="is it true?")
        new_state = router_node(state)

        assert new_state.route == "clarify"
        meta = new_state.run_metadata["router"]
        assert meta["reason_code"] == "underspecified_query"

    def test_non_historical_intent_routes_to_out_of_scope(self):
        state = AgentState(user_query="write me a poem about WW2")
        new_state = router_node(state)

        assert new_state.route == "out_of_scope"
        meta = new_state.run_metadata["router"]
        assert meta["reason_code"] == "non_historical_intent"

    def test_default_routes_to_fact_check(self):
        state = AgentState(user_query="When did the Berlin Wall fall?")
        new_state = router_node(state)

        assert new_state.route == "fact_check"
        meta = new_state.run_metadata["router"]
        assert meta["reason_code"] == "default_fact_check"
        assert meta["features"]["starts_like_question"] is True

    # -------------------------------------------------------------------------
    # Additional tests
    # -------------------------------------------------------------------------

    def test_ambiguous_reference_routes_to_clarify(self):
        # Contains a vague "this" – should trigger ambiguous_reference clarify path
        state = AgentState(user_query="Did this really happen?")
        new_state = router_node(state)

        assert new_state.route == "clarify"
        meta = new_state.run_metadata["router"]
        assert meta["reason_code"] == "ambiguous_reference"

    def test_coding_request_routes_to_out_of_scope_with_intent_type(self):
        # Clearly a coding / implementation request, not historical fact-checking
        state = AgentState(user_query="Write a Python script that prints prime numbers")
        new_state = router_node(state)

        assert new_state.route == "out_of_scope"
        meta = new_state.run_metadata["router"]

        # Generic reason_code for non-historical queries
        assert meta["reason_code"] == "non_historical_intent"

        # More fine-grained category for debugging / UI
        # This assumes router sets meta["intent_type"] = "coding_request"
        assert meta.get("intent_type") == "coding_request"

    def test_chat_request_routes_to_out_of_scope_with_intent_type(self):
        # Generic chat / joke request, even if it mentions a historical entity
        state = AgentState(user_query="tell me a joke about Napoleon")
        new_state = router_node(state)

        assert new_state.route == "out_of_scope"
        meta = new_state.run_metadata["router"]

        assert meta["reason_code"] == "non_historical_intent"
        # This assumes router sets meta["intent_type"] = "chat_request"
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
