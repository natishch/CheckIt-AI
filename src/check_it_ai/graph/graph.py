"""LangGraph workflow assembly with streaming and checkpointing support."""

from __future__ import annotations

from typing import Literal

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph
from langgraph.graph.state import CompiledStateGraph

from src.check_it_ai.graph.state import AgentState
from src.check_it_ai.types.router import RouterDecision

# =============================================================================
# Node Imports (lazy to avoid circular imports)
# =============================================================================


def _get_router_node():
    from src.check_it_ai.graph.nodes.router import router_node

    return router_node


def _get_researcher_node():
    from src.check_it_ai.graph.nodes.researcher import researcher_node

    return researcher_node


def _get_analyst_node():
    from src.check_it_ai.graph.nodes.fact_analyst import fact_analyst_node

    return fact_analyst_node


def _get_writer_node():
    from src.check_it_ai.graph.nodes.writer import writer_node

    return writer_node


# =============================================================================
# Routing Function
# =============================================================================


def _route_after_router(state: AgentState) -> Literal["researcher", "__end__"]:
    """Determine next node after router based on routing decision.

    Routes:
        - fact_check -> researcher (continue pipeline)
        - clarify -> END (need user clarification)
        - out_of_scope -> END (outside system scope)
    """
    if state.route == RouterDecision.FACT_CHECK:
        return "researcher"

    # Both "clarify" and "out_of_scope" terminate the graph
    return END


# =============================================================================
# Graph Builder
# =============================================================================


def build_graph() -> StateGraph:
    """Build the LangGraph state machine (not compiled).

    Returns:
        StateGraph ready for compilation with optional checkpointer.

    Graph Structure:
        START -> router -> [conditional]
                           |-- fact_check -> researcher -> analyst -> writer -> END
                           |-- clarify -> END
                           +-- out_of_scope -> END
    """
    # Create graph with AgentState schema
    graph = StateGraph(AgentState)

    # -----------------------------------------------------------------
    # Add Nodes
    # -----------------------------------------------------------------
    graph.add_node("router", _get_router_node())
    graph.add_node("researcher", _get_researcher_node())
    graph.add_node("analyst", _get_analyst_node())
    graph.add_node("writer", _get_writer_node())

    # -----------------------------------------------------------------
    # Set Entry Point
    # -----------------------------------------------------------------
    graph.set_entry_point("router")

    # -----------------------------------------------------------------
    # Add Edges
    # -----------------------------------------------------------------

    # Conditional edge after router
    graph.add_conditional_edges(
        source="router",
        path=_route_after_router,
        path_map={
            "researcher": "researcher",
            END: END,
        },
    )

    # Linear edges for fact-check path
    graph.add_edge("researcher", "analyst")
    graph.add_edge("analyst", "writer")
    graph.add_edge("writer", END)

    return graph


# =============================================================================
# Compiled Graph Factory
# =============================================================================


def compile_graph(
    checkpointer: bool = False,
) -> CompiledStateGraph:
    """Build and compile the graph with optional features.

    Args:
        checkpointer: If True, enable memory-based checkpointing for
                     state persistence and session management.

    Returns:
        Compiled graph ready for invoke/ainvoke/stream.

    Example:
        # Without checkpointing (stateless)
        graph = compile_graph()
        result = graph.invoke({"user_query": "When did WWII end?"})

        # With checkpointing (stateful sessions)
        graph = compile_graph(checkpointer=True)
        config = {"configurable": {"thread_id": "session-123"}}
        result = graph.invoke({"user_query": "When did WWII end?"}, config)
    """
    graph = build_graph()

    if checkpointer:
        memory = MemorySaver()
        return graph.compile(checkpointer=memory)

    return graph.compile()


# =============================================================================
# Default Compiled Instance
# =============================================================================

# Lazy singleton for simple use cases
_default_graph: CompiledStateGraph | None = None


def get_default_graph() -> CompiledStateGraph:
    """Get or create the default compiled graph (without checkpointing).

    Returns:
        Cached compiled graph instance.
    """
    global _default_graph
    if _default_graph is None:
        _default_graph = compile_graph(checkpointer=False)
    return _default_graph
