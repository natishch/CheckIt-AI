"""LangGraph workflow orchestration."""


def run_graph(query: str) -> dict:
    """
    Dummy graph execution function.

    Args:
        query: User query string

    Returns:
        Dictionary with final_answer
    """
    return {"final_answer": f"Placeholder response for: {query}"}
