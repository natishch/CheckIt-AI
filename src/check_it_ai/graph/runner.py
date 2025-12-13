"""Graph execution utilities with streaming and async support."""

from __future__ import annotations

import time
from collections.abc import AsyncIterator, Iterator
from typing import Any

from src.check_it_ai.graph.graph import compile_graph
from src.check_it_ai.graph.state import AgentState
from src.check_it_ai.types.graph import (
    GraphCompleteEvent,
    GraphResult,
    NodeEndEvent,
    NodeStartEvent,
    StreamEvent,
)
from src.check_it_ai.types.router import RouterDecision

# =============================================================================
# Sync Execution
# =============================================================================


def run_graph(
    query: str,
    *,
    checkpointer: bool = False,
    thread_id: str | None = None,
    include_state: bool = False,
) -> GraphResult:
    """Execute the fact-checking graph synchronously.

    Args:
        query: User query to fact-check.
        checkpointer: Enable state persistence.
        thread_id: Session ID for checkpointing (required if checkpointer=True).
        include_state: Include full AgentState in result (for debugging).

    Returns:
        GraphResult with answer, confidence, citations, and metadata.

    Example:
        result = run_graph("When did World War II end?")
        print(result.final_answer)
        print(f"Confidence: {result.confidence:.0%}")
    """
    start_time = time.perf_counter()

    # Compile graph
    graph = compile_graph(checkpointer=checkpointer)

    # Build config
    config: dict[str, Any] = {}
    if checkpointer and thread_id:
        config["configurable"] = {"thread_id": thread_id}

    # Execute
    initial_state = AgentState(user_query=query)
    final_state = graph.invoke(initial_state, config)

    total_time = time.perf_counter() - start_time

    return _build_result(final_state, total_time, include_state)


# =============================================================================
# Async Execution
# =============================================================================


async def arun_graph(
    query: str,
    *,
    checkpointer: bool = False,
    thread_id: str | None = None,
    include_state: bool = False,
) -> GraphResult:
    """Execute the fact-checking graph asynchronously.

    Args:
        query: User query to fact-check.
        checkpointer: Enable state persistence.
        thread_id: Session ID for checkpointing.
        include_state: Include full AgentState in result.

    Returns:
        GraphResult with answer, confidence, citations, and metadata.

    Example:
        result = await arun_graph("When did World War II end?")
        print(result.final_answer)
    """
    start_time = time.perf_counter()

    # Compile graph
    graph = compile_graph(checkpointer=checkpointer)

    # Build config
    config: dict[str, Any] = {}
    if checkpointer and thread_id:
        config["configurable"] = {"thread_id": thread_id}

    # Execute async
    initial_state = AgentState(user_query=query)
    final_state = await graph.ainvoke(initial_state, config)

    total_time = time.perf_counter() - start_time

    return _build_result(final_state, total_time, include_state)


# =============================================================================
# Streaming Execution
# =============================================================================


def stream_graph(
    query: str,
    *,
    checkpointer: bool = False,
    thread_id: str | None = None,
) -> Iterator[StreamEvent]:
    """Execute graph with streaming progress updates.

    Yields events as each node starts and completes, allowing
    real-time progress display.

    Args:
        query: User query to fact-check.
        checkpointer: Enable state persistence.
        thread_id: Session ID for checkpointing.

    Yields:
        StreamEvent instances (NodeStartEvent, NodeEndEvent, GraphCompleteEvent).

    Example:
        for event in stream_graph("When did WWII end?"):
            if isinstance(event, NodeStartEvent):
                print(f"Starting {event.node_name}...")
            elif isinstance(event, NodeEndEvent):
                print(f"Completed {event.node_name} ({event.duration_ms:.0f}ms)")
            elif isinstance(event, GraphCompleteEvent):
                print(f"Done! Answer: {event.result.final_answer}")
    """
    start_time = time.perf_counter()

    # Compile graph
    graph = compile_graph(checkpointer=checkpointer)

    # Build config
    config: dict[str, Any] = {}
    if checkpointer and thread_id:
        config["configurable"] = {"thread_id": thread_id}

    # Track node timing
    node_start_times: dict[str, float] = {}
    accumulated_state: dict[str, Any] = {"user_query": query}

    # Stream execution
    initial_state = AgentState(user_query=query)

    for event in graph.stream(initial_state, config, stream_mode="updates"):
        for node_name, node_output in event.items():
            current_time = time.perf_counter()

            # Emit start event (first time seeing this node)
            if node_name not in node_start_times:
                node_start_times[node_name] = current_time
                yield NodeStartEvent(
                    node_name=node_name,
                    timestamp=current_time,
                )

            # Emit end event
            duration = (current_time - node_start_times[node_name]) * 1000
            output_keys = list(node_output.keys()) if isinstance(node_output, dict) else []
            yield NodeEndEvent(
                node_name=node_name,
                timestamp=current_time,
                duration_ms=duration,
                output_keys=output_keys,
            )

            # Accumulate state from node outputs
            if isinstance(node_output, dict):
                accumulated_state.update(node_output)

    # Build final state from accumulated outputs
    total_time = time.perf_counter() - start_time

    # Reconstruct AgentState from accumulated state
    final_state = _reconstruct_state(accumulated_state)
    result = _build_result(final_state, total_time, include_state=False)

    yield GraphCompleteEvent(
        result=result,
        total_duration_ms=total_time * 1000,
    )


async def astream_graph(
    query: str,
    *,
    checkpointer: bool = False,
    thread_id: str | None = None,
) -> AsyncIterator[StreamEvent]:
    """Execute graph with async streaming progress updates.

    Args:
        query: User query to fact-check.
        checkpointer: Enable state persistence.
        thread_id: Session ID for checkpointing.

    Yields:
        StreamEvent instances asynchronously.

    Example:
        async for event in astream_graph("When did WWII end?"):
            if isinstance(event, NodeEndEvent):
                print(f"Completed {event.node_name}")
    """
    start_time = time.perf_counter()

    graph = compile_graph(checkpointer=checkpointer)

    config: dict[str, Any] = {}
    if checkpointer and thread_id:
        config["configurable"] = {"thread_id": thread_id}

    node_start_times: dict[str, float] = {}
    accumulated_state: dict[str, Any] = {"user_query": query}

    initial_state = AgentState(user_query=query)

    async for event in graph.astream(initial_state, config, stream_mode="updates"):
        for node_name, node_output in event.items():
            current_time = time.perf_counter()

            if node_name not in node_start_times:
                node_start_times[node_name] = current_time
                yield NodeStartEvent(
                    node_name=node_name,
                    timestamp=current_time,
                )

            duration = (current_time - node_start_times[node_name]) * 1000
            output_keys = list(node_output.keys()) if isinstance(node_output, dict) else []
            yield NodeEndEvent(
                node_name=node_name,
                timestamp=current_time,
                duration_ms=duration,
                output_keys=output_keys,
            )

            if isinstance(node_output, dict):
                accumulated_state.update(node_output)

    total_time = time.perf_counter() - start_time

    final_state = _reconstruct_state(accumulated_state)
    result = _build_result(final_state, total_time, include_state=False)

    yield GraphCompleteEvent(
        result=result,
        total_duration_ms=total_time * 1000,
    )


# =============================================================================
# Helper Functions
# =============================================================================


def _reconstruct_state(accumulated: dict[str, Any]) -> AgentState:
    """Reconstruct AgentState from accumulated node outputs."""
    state = AgentState(user_query=accumulated.get("user_query", ""))

    # Copy over known fields
    if "route" in accumulated:
        state.route = accumulated["route"]
    if "clarify_request" in accumulated:
        state.clarify_request = accumulated["clarify_request"]
    if "search_queries" in accumulated:
        state.search_queries = accumulated["search_queries"]
    if "search_results" in accumulated:
        state.search_results = accumulated["search_results"]
    if "evidence_bundle" in accumulated:
        state.evidence_bundle = accumulated["evidence_bundle"]
    if "final_answer" in accumulated:
        state.final_answer = accumulated["final_answer"]
    if "confidence" in accumulated:
        state.confidence = accumulated["confidence"]
    if "citations" in accumulated:
        state.citations = accumulated["citations"]
    if "run_metadata" in accumulated:
        state.run_metadata = accumulated["run_metadata"]

    return state


def _dict_to_state(data: dict) -> AgentState:
    """Convert a dict (from graph.invoke) to AgentState."""
    state = AgentState(user_query=data.get("user_query", ""))

    # Copy fields that exist in the dict
    if "route" in data:
        state.route = data["route"]
    if "clarify_request" in data:
        state.clarify_request = data["clarify_request"]
    if "search_queries" in data:
        state.search_queries = data["search_queries"]
    if "search_results" in data:
        state.search_results = data["search_results"]
    if "evidence_bundle" in data:
        state.evidence_bundle = data["evidence_bundle"]
    if "final_answer" in data:
        state.final_answer = data["final_answer"]
    if "confidence" in data:
        state.confidence = data["confidence"]
    if "citations" in data:
        state.citations = data["citations"]
    if "run_metadata" in data:
        state.run_metadata = data["run_metadata"]
    if "writer_output" in data:
        state.writer_output = data["writer_output"]

    return state


def _build_result(
    state: AgentState | dict,
    total_time: float,
    include_state: bool,
) -> GraphResult:
    """Build GraphResult from final AgentState or dict."""
    # Handle dict returned by graph.invoke
    if isinstance(state, dict):
        state = _dict_to_state(state)

    # Get route as string
    route_value = state.route
    if isinstance(route_value, RouterDecision):
        route = route_value.value
    elif route_value is None:
        route = "unknown"
    else:
        route = str(route_value)

    # Handle clarify route
    if route == "clarify":
        clarify = state.clarify_request
        suggested_prompt = ""
        clarify_dict = None

        if clarify is not None:
            if hasattr(clarify, "suggested_prompt"):
                suggested_prompt = clarify.suggested_prompt
            if hasattr(clarify, "model_dump"):
                clarify_dict = clarify.model_dump()

        return GraphResult(
            final_answer=suggested_prompt or "Could you please clarify your question?",
            confidence=0.0,
            route=route,
            clarify_request=clarify_dict,
            metadata={
                "total_time_seconds": total_time,
                "router": state.run_metadata.get("router", {}),
            },
            internal_state=state if include_state else None,
        )

    # Handle out_of_scope route
    if route == "out_of_scope":
        router_meta = state.run_metadata.get("router", {})
        intent_type = router_meta.get("intent_type", "non-historical")
        return GraphResult(
            final_answer=(
                f"This question appears to be about {intent_type}, which is outside my scope "
                "as a historical fact-checker. I specialize in verifying historical claims and events."
            ),
            confidence=0.0,
            route=route,
            metadata={
                "total_time_seconds": total_time,
                "router": router_meta,
            },
            internal_state=state if include_state else None,
        )

    # Handle fact_check route
    citations = []
    if state.citations:
        for c in state.citations:
            if hasattr(c, "model_dump"):
                citations.append(c.model_dump())
            else:
                citations.append(dict(c) if isinstance(c, dict) else {"value": str(c)})

    evidence = None
    if state.evidence_bundle:
        if hasattr(state.evidence_bundle, "model_dump"):
            evidence = state.evidence_bundle.model_dump()
        elif isinstance(state.evidence_bundle, dict):
            evidence = state.evidence_bundle

    return GraphResult(
        final_answer=state.final_answer or "Unable to generate an answer.",
        confidence=state.confidence,
        route=route,
        citations=citations,
        evidence_bundle=evidence,
        metadata={
            "total_time_seconds": total_time,
            "router": state.run_metadata.get("router", {}),
            "analyst": state.run_metadata.get("analyst", {}),
            "writer": state.run_metadata.get("writer", {}),
            "search_queries_count": len(state.search_queries) if state.search_queries else 0,
            "search_results_count": len(state.search_results) if state.search_results else 0,
        },
        internal_state=state if include_state else None,
    )
