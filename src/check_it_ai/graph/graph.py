"""LangGraph workflow orchestration."""
# src/agentic_historian/graph/graph.py (sketch)
from langgraph.graph import StateGraph, END

from src.check_it_ai.graph.state import AgentState
from src.check_it_ai.graph.nodes.router import router_node
from src.check_it_ai.graph.nodes.researcher import researcher_node
from src.check_it_ai.graph.nodes.fact_analyst import fact_analyst_node
from src.check_it_ai.graph.nodesriter import writer_node

def build_graph():
    graph = StateGraph(AgentState)

    graph.add_node("router", router_node)
    graph.add_node("researcher", researcher_node)
    graph.add_node("analyst", fact_analyst_node)
    graph.add_node("writer", writer_node)

    graph.set_entry_point("router")

    def route_decision(state: AgentState) -> str:
        if state.route == "clarify":
            return "clarify"
        if state.route == "out_of_scope":
            return "out_of_scope"
        return "fact_check"

    graph.add_conditional_edges(
        "router",
        route_decision,
        {
            "clarify": END,
            "out_of_scope": END,
            "fact_check": "researcher",
        },
    )

    graph.add_edge("researcher", "analyst")
    graph.add_edge("analyst", "writer")
    graph.add_edge("writer", END)

    return graph


#TODO
def run_graph(query: str) -> dict:
    """
    Dummy graph execution function.

    Args:
        query: User query string

    Returns:
        Dictionary with final_answer
    """
    return {"final_answer": f"Placeholder response for: {query}"}
