"""Router node for intent classification."""


def route_query(state: dict) -> dict:
    """Route user query to appropriate path."""
    return {"route": "fact_check"}
