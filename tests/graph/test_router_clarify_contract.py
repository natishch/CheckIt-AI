# tests/graph/test_router_clarify_contract.py
from src.check_it_ai.graph.state import AgentState
from src.check_it_ai.graph.nodes.router import router_node


class TestSearchQuery:
    """Tests for clarify path & contract."""

    def test_empty_query_routes_to_clarify_and_creates_clarify_request(self):
        state = AgentState(user_query="   ")
        new_state = router_node(state)

        assert new_state.route == "clarify"
        assert "router" in new_state.run_metadata

        meta = new_state.run_metadata["router"]
        assert meta["reason_code"] == "empty_query"

        cr = new_state.clarify_request
        assert cr is not None
        assert cr.reason_code == "empty_query"
        # original_query should preserve raw whitespace
        assert cr.original_query == "   "
        # Should at least ask for the claim
        keys = {field.key for field in cr.fields}
        assert "claim" in keys

    def test_underspecified_query_routes_to_clarify_and_uses_underspecified_code(self):
        state = AgentState(user_query="is it true?")
        new_state = router_node(state)

        assert new_state.route == "clarify"

        meta = new_state.run_metadata["router"]
        assert meta["reason_code"] == "underspecified_query"

        cr = new_state.clarify_request
        assert cr is not None
        # We normalize underspecified / ambiguous into the ClarifyRequest’s reason_code domain
        assert cr.reason_code == "underspecified_query"
        msg = cr.message.lower()
        assert "too short" in msg or "bit too short" in msg
        assert any(field.key == "claim" for field in cr.fields)

    def test_ambiguous_reference_uses_ambiguous_reference_reason_code(self):
        state = AgentState(user_query="Did it really happen?")
        new_state = router_node(state)

        assert new_state.route == "clarify"

        meta = new_state.run_metadata["router"]
        # Depending on heuristics, this should be ambiguous_reference or underspecified
        assert meta["reason_code"] in {"ambiguous_reference", "underspecified_query"}

        cr = new_state.clarify_request
        assert cr is not None
        assert cr.original_query == "Did it really happen?"
        assert any(field.key == "claim" for field in cr.fields)

    def test_non_historical_coding_request_goes_out_of_scope(self):
        state = AgentState(user_query="Write a Python script that prints all primes")
        new_state = router_node(state)

        assert new_state.route == "out_of_scope"
        meta = new_state.run_metadata["router"]
        assert meta["reason_code"].startswith("non_historical_")
        assert "coding" in meta["reason_code"] or "coding" in meta["reason_text"].lower()
        assert new_state.clarify_request is None

    def test_fact_check_default_for_clear_historical_question(self):
        state = AgentState(user_query="When did the Berlin Wall fall?")
        new_state = router_node(state)

        assert new_state.route == "fact_check"
        meta = new_state.run_metadata["router"]
        assert meta["reason_code"] == "default_fact_check"
        assert new_state.clarify_request is None
