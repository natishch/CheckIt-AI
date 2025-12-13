# AH-09: LangGraph Assembly & CLI Runner - Technical Design Document

**Task**: Assemble the complete LangGraph workflow with streaming, checkpointing, and async support + CLI runner
**Date**: 2025-12-13
**Status**: 📋 Design Complete
**Branch**: ah-09-langgraph-assembly-cli-runner

---

## Overview

This task builds the **LangGraph pipeline** that orchestrates all nodes into a working fact-checking system, plus a **CLI runner** for demonstrations and testing.

### Goals

1. **Graph Assembly**: Wire Router → Researcher → Fact Analyst → Writer
2. **Streaming**: Real-time progress output showing each node's execution
3. **Checkpointing**: Memory-based state persistence for session management
4. **Async Support**: Both sync and async graph invocation
5. **CLI Runner**: Command-line interface for demos with live progress display
6. **Error Handling**: Graceful fallbacks with single retry on API failures

---

## A. Architecture Overview

### Pipeline Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           CHECK-IT-AI PIPELINE                              │
│                                                                             │
│  ┌─────────┐      ┌────────────┐      ┌──────────┐      ┌────────┐         │
│  │  USER   │      │   ROUTER   │      │RESEARCHER│      │ANALYST │         │
│  │  QUERY  │─────▶│            │─────▶│          │─────▶│        │         │
│  └─────────┘      └────────────┘      └──────────┘      └────────┘         │
│                          │                                   │              │
│                          │ clarify/                          │              │
│                          │ out_of_scope                      ▼              │
│                          │                            ┌──────────┐          │
│                          └───────────────────────────▶│  WRITER  │          │
│                                    END                └──────────┘          │
│                                                              │              │
│                                                              ▼              │
│                                                         ┌────────┐         │
│                                                         │ OUTPUT │         │
│                                                         └────────┘         │
└─────────────────────────────────────────────────────────────────────────────┘
```

### State Flow by Node

| Node | Reads | Writes |
|------|-------|--------|
| **Router** | `user_query` | `route`, `clarify_request`, `run_metadata["router"]` |
| **Researcher** | `user_query`, `route` | `search_queries`, `search_results` |
| **Fact Analyst** | `user_query`, `search_results` | `evidence_bundle`, `run_metadata["analyst"]` |
| **Writer** | `user_query`, `evidence_bundle` | `final_answer`, `citations`, `confidence`, `writer_output`, `run_metadata["writer"]` |

### Routing Logic

```
Router Decision:
├── "clarify"      → END (return clarification request)
├── "out_of_scope" → END (return scope message)
└── "fact_check"   → Researcher → Analyst → Writer → END
```

---

## B. Graph Implementation

### Core Graph Builder

```python
# src/check_it_ai/graph/graph.py

"""LangGraph workflow assembly with streaming and checkpointing support."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Literal

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph

from src.check_it_ai.graph.state import AgentState

if TYPE_CHECKING:
    from langgraph.graph.state import CompiledStateGraph


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
        - fact_check → researcher (continue pipeline)
        - clarify → END (need user clarification)
        - out_of_scope → END (outside system scope)
    """
    route = state.route

    if route == "fact_check":
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
        START → router → [conditional]
                           ├── fact_check → researcher → analyst → writer → END
                           ├── clarify → END
                           └── out_of_scope → END
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
```

### Graph Runner Functions

```python
# src/check_it_ai/graph/runner.py

"""Graph execution utilities with streaming and async support."""

from __future__ import annotations

import asyncio
import time
from typing import TYPE_CHECKING, Any, AsyncIterator, Iterator

from src.check_it_ai.graph.graph import compile_graph
from src.check_it_ai.graph.state import AgentState

if TYPE_CHECKING:
    from langgraph.graph.state import CompiledStateGraph


# =============================================================================
# Result Dataclass
# =============================================================================

from dataclasses import dataclass, field


@dataclass
class GraphResult:
    """Structured result from graph execution."""

    # Core outputs
    final_answer: str
    confidence: float
    route: str

    # Citations (empty for clarify/out_of_scope)
    citations: list[dict[str, Any]] = field(default_factory=list)

    # Evidence (None for clarify/out_of_scope)
    evidence_bundle: dict[str, Any] | None = None

    # Execution metadata
    metadata: dict[str, Any] = field(default_factory=dict)

    # For clarify route
    clarify_request: dict[str, Any] | None = None

    # Full state (for debugging)
    _state: AgentState | None = field(default=None, repr=False)

    @property
    def is_fact_check(self) -> bool:
        return self.route == "fact_check"

    @property
    def is_clarify(self) -> bool:
        return self.route == "clarify"

    @property
    def is_out_of_scope(self) -> bool:
        return self.route == "out_of_scope"

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "final_answer": self.final_answer,
            "confidence": self.confidence,
            "route": self.route,
            "citations": self.citations,
            "evidence_bundle": self.evidence_bundle,
            "metadata": self.metadata,
            "clarify_request": self.clarify_request,
        }


# =============================================================================
# Streaming Event Types
# =============================================================================

@dataclass
class NodeStartEvent:
    """Event emitted when a node starts execution."""
    node_name: str
    timestamp: float


@dataclass
class NodeEndEvent:
    """Event emitted when a node completes execution."""
    node_name: str
    timestamp: float
    duration_ms: float
    output_keys: list[str]


@dataclass
class GraphCompleteEvent:
    """Event emitted when graph execution completes."""
    result: GraphResult
    total_duration_ms: float


StreamEvent = NodeStartEvent | NodeEndEvent | GraphCompleteEvent


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
    config = {}
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
    config = {}
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
                print(f"⏳ {event.node_name}...")
            elif isinstance(event, NodeEndEvent):
                print(f"✓ {event.node_name} ({event.duration_ms:.0f}ms)")
            elif isinstance(event, GraphCompleteEvent):
                print(f"Done! Answer: {event.result.final_answer}")
    """
    start_time = time.perf_counter()

    # Compile graph
    graph = compile_graph(checkpointer=checkpointer)

    # Build config
    config = {}
    if checkpointer and thread_id:
        config["configurable"] = {"thread_id": thread_id}

    # Track node timing
    node_start_times: dict[str, float] = {}
    final_state: AgentState | None = None

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
            yield NodeEndEvent(
                node_name=node_name,
                timestamp=current_time,
                duration_ms=duration,
                output_keys=list(node_output.keys()) if isinstance(node_output, dict) else [],
            )

            # Track final state from last node output
            if isinstance(node_output, dict):
                if final_state is None:
                    final_state = AgentState(user_query=query)
                # Merge outputs into state
                for key, value in node_output.items():
                    if hasattr(final_state, key):
                        setattr(final_state, key, value)

    # Get complete final state
    # Note: For proper state, we need to get it from the graph
    total_time = time.perf_counter() - start_time

    # Build result from tracked state
    if final_state:
        result = _build_result(final_state, total_time, include_state=False)
    else:
        result = GraphResult(
            final_answer="Graph execution produced no output",
            confidence=0.0,
            route="unknown",
            metadata={"error": "no_output"},
        )

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
                print(f"✓ {event.node_name}")
    """
    start_time = time.perf_counter()

    graph = compile_graph(checkpointer=checkpointer)

    config = {}
    if checkpointer and thread_id:
        config["configurable"] = {"thread_id": thread_id}

    node_start_times: dict[str, float] = {}
    final_state: AgentState | None = None

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
            yield NodeEndEvent(
                node_name=node_name,
                timestamp=current_time,
                duration_ms=duration,
                output_keys=list(node_output.keys()) if isinstance(node_output, dict) else [],
            )

            if isinstance(node_output, dict):
                if final_state is None:
                    final_state = AgentState(user_query=query)
                for key, value in node_output.items():
                    if hasattr(final_state, key):
                        setattr(final_state, key, value)

    total_time = time.perf_counter() - start_time

    if final_state:
        result = _build_result(final_state, total_time, include_state=False)
    else:
        result = GraphResult(
            final_answer="Graph execution produced no output",
            confidence=0.0,
            route="unknown",
        )

    yield GraphCompleteEvent(
        result=result,
        total_duration_ms=total_time * 1000,
    )


# =============================================================================
# Result Builder
# =============================================================================

def _build_result(
    state: AgentState,
    total_time: float,
    include_state: bool,
) -> GraphResult:
    """Build GraphResult from final AgentState."""

    route = state.route if hasattr(state, 'route') else "unknown"

    # Handle clarify route
    if route == "clarify":
        clarify = state.clarify_request
        return GraphResult(
            final_answer=clarify.suggested_prompt if clarify else "Could you please clarify your question?",
            confidence=0.0,
            route=route,
            clarify_request=clarify.model_dump() if clarify else None,
            metadata={
                "total_time_seconds": total_time,
                "router": state.run_metadata.get("router", {}),
            },
            _state=state if include_state else None,
        )

    # Handle out_of_scope route
    if route == "out_of_scope":
        router_meta = state.run_metadata.get("router", {})
        intent_type = router_meta.get("intent_type", "non-historical")
        return GraphResult(
            final_answer=f"This question appears to be about {intent_type}, which is outside my scope as a historical fact-checker. I specialize in verifying historical claims and events.",
            confidence=0.0,
            route=route,
            metadata={
                "total_time_seconds": total_time,
                "router": router_meta,
            },
            _state=state if include_state else None,
        )

    # Handle fact_check route
    citations = []
    if state.citations:
        citations = [c.model_dump() for c in state.citations]

    evidence = None
    if state.evidence_bundle:
        evidence = state.evidence_bundle.model_dump()

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
            "search_queries_count": len(state.search_queries),
            "search_results_count": len(state.search_results),
        },
        _state=state if include_state else None,
    )
```

---

## C. Error Handling & Retry Logic

### Retry Decorator

```python
# src/check_it_ai/graph/retry.py

"""Retry utilities for graph node execution."""

from __future__ import annotations

import asyncio
import functools
import logging
import time
from typing import Callable, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")


class RetryableError(Exception):
    """Exception that indicates the operation should be retried."""
    pass


def with_retry(
    max_attempts: int = 2,
    delay_seconds: float = 1.0,
    retryable_exceptions: tuple[type[Exception], ...] = (RetryableError,),
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """Decorator to add retry logic to a function.

    Args:
        max_attempts: Maximum number of attempts (including first try).
        delay_seconds: Delay between retries.
        retryable_exceptions: Exception types that trigger retry.

    Example:
        @with_retry(max_attempts=2)
        def call_api():
            response = httpx.get(url)
            if response.status_code == 429:
                raise RetryableError("Rate limited")
            return response
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> T:
            last_exception = None

            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except retryable_exceptions as e:
                    last_exception = e
                    if attempt < max_attempts:
                        logger.warning(
                            f"{func.__name__} failed (attempt {attempt}/{max_attempts}): {e}. "
                            f"Retrying in {delay_seconds}s..."
                        )
                        time.sleep(delay_seconds)
                    else:
                        logger.error(
                            f"{func.__name__} failed after {max_attempts} attempts: {e}"
                        )

            raise last_exception

        return wrapper
    return decorator


def with_retry_async(
    max_attempts: int = 2,
    delay_seconds: float = 1.0,
    retryable_exceptions: tuple[type[Exception], ...] = (RetryableError,),
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """Async version of retry decorator."""
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            last_exception = None

            for attempt in range(1, max_attempts + 1):
                try:
                    return await func(*args, **kwargs)
                except retryable_exceptions as e:
                    last_exception = e
                    if attempt < max_attempts:
                        logger.warning(
                            f"{func.__name__} failed (attempt {attempt}/{max_attempts}): {e}. "
                            f"Retrying in {delay_seconds}s..."
                        )
                        await asyncio.sleep(delay_seconds)
                    else:
                        logger.error(
                            f"{func.__name__} failed after {max_attempts} attempts: {e}"
                        )

            raise last_exception

        return wrapper
    return decorator
```

### Node-Level Error Handling

Each node should handle its own errors gracefully. Example pattern:

```python
# Pattern for nodes with error handling

def researcher_node(state: AgentState) -> dict[str, Any]:
    """Researcher node with error handling."""
    try:
        # Normal execution
        results = google_search(state.user_query)
        return {"search_results": results}

    except QuotaExceededError:
        # Fallback: try DuckDuckGo
        logger.warning("Google quota exceeded, trying DuckDuckGo fallback")
        try:
            results = duckduckgo_search(state.user_query)
            return {"search_results": results}
        except Exception as e:
            logger.error(f"All search backends failed: {e}")
            return {"search_results": []}  # Empty results, let Writer handle

    except Exception as e:
        logger.error(f"Researcher failed: {e}")
        return {"search_results": []}
```

---

## D. CLI Runner Design

### CLI Module

```python
# src/check_it_ai/cli.py

#!/usr/bin/env python3
"""Command-line interface for Check-It-AI fact-checking system.

Usage:
    # Single query
    uv run python -m check_it_ai "When did World War II end?"

    # With streaming progress
    uv run python -m check_it_ai --stream "Was Napoleon short?"

    # Interactive mode
    uv run python -m check_it_ai --interactive

    # JSON output
    uv run python -m check_it_ai --format json "When did Rome fall?"
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import TextIO

from src.check_it_ai.graph.runner import (
    GraphCompleteEvent,
    GraphResult,
    NodeEndEvent,
    NodeStartEvent,
    run_graph,
    stream_graph,
)


# =============================================================================
# Output Formatting
# =============================================================================

# ANSI color codes for terminal output
class Colors:
    HEADER = "\033[95m"
    BLUE = "\033[94m"
    CYAN = "\033[96m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    RESET = "\033[0m"


def supports_color() -> bool:
    """Check if terminal supports colors."""
    import os
    return hasattr(sys.stdout, "isatty") and sys.stdout.isatty() and os.environ.get("TERM") != "dumb"


def colorize(text: str, color: str) -> str:
    """Apply color if supported."""
    if supports_color():
        return f"{color}{text}{Colors.RESET}"
    return text


# Node display names and icons
NODE_DISPLAY = {
    "router": ("🔀", "Router", "Analyzing query..."),
    "researcher": ("🔍", "Researcher", "Searching for evidence..."),
    "analyst": ("🔬", "Analyst", "Evaluating evidence..."),
    "writer": ("✍️", "Writer", "Generating answer..."),
}


def format_result_pretty(result: GraphResult, file: TextIO = sys.stdout) -> None:
    """Format result for human-readable terminal output."""

    # Header
    print(colorize("=" * 60, Colors.DIM), file=file)

    # Route indicator
    route_colors = {
        "fact_check": Colors.GREEN,
        "clarify": Colors.YELLOW,
        "out_of_scope": Colors.RED,
    }
    route_color = route_colors.get(result.route, Colors.RESET)
    print(colorize(f"Route: {result.route.upper()}", route_color + Colors.BOLD), file=file)

    print(colorize("=" * 60, Colors.DIM), file=file)
    print(file=file)

    # Answer
    print(colorize("ANSWER:", Colors.BOLD), file=file)
    print(colorize("-" * 40, Colors.DIM), file=file)
    print(result.final_answer, file=file)
    print(file=file)

    # Confidence (only for fact_check)
    if result.is_fact_check and result.confidence > 0:
        conf_pct = result.confidence * 100
        conf_color = Colors.GREEN if conf_pct >= 70 else Colors.YELLOW if conf_pct >= 40 else Colors.RED
        print(colorize(f"Confidence: {conf_pct:.1f}%", conf_color), file=file)
        print(file=file)

    # Citations
    if result.citations:
        print(colorize("CITATIONS:", Colors.BOLD), file=file)
        print(colorize("-" * 40, Colors.DIM), file=file)
        for cite in result.citations:
            eid = cite.get("evidence_id", "?")
            title = cite.get("title", "Untitled")
            url = cite.get("url", "")
            print(f"  [{eid}] {title}", file=file)
            print(colorize(f"       {url}", Colors.DIM), file=file)
        print(file=file)

    # Metadata
    meta = result.metadata
    if meta:
        print(colorize("METADATA:", Colors.DIM), file=file)
        print(colorize("-" * 40, Colors.DIM), file=file)
        if "total_time_seconds" in meta:
            print(colorize(f"  Total time: {meta['total_time_seconds']:.2f}s", Colors.DIM), file=file)
        if "search_results_count" in meta:
            print(colorize(f"  Search results: {meta['search_results_count']}", Colors.DIM), file=file)
        print(file=file)

    print(colorize("=" * 60, Colors.DIM), file=file)


def format_result_json(result: GraphResult, file: TextIO = sys.stdout) -> None:
    """Format result as JSON."""
    print(json.dumps(result.to_dict(), indent=2, default=str), file=file)


# =============================================================================
# Execution Modes
# =============================================================================

def run_single_query(
    query: str,
    output_format: str = "pretty",
    use_streaming: bool = False,
    debug: bool = False,
) -> int:
    """Run a single query and display the result.

    Returns:
        Exit code (0 for success, 1 for error).
    """
    try:
        if use_streaming:
            return _run_with_streaming(query, output_format)
        else:
            result = run_graph(query, include_state=debug)
            _output_result(result, output_format)
            return 0

    except KeyboardInterrupt:
        print("\n\nInterrupted.", file=sys.stderr)
        return 130
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        if debug:
            import traceback
            traceback.print_exc()
        return 1


def _run_with_streaming(query: str, output_format: str) -> int:
    """Run query with streaming progress display."""

    print(colorize("\n🚀 Starting fact-check pipeline...\n", Colors.BOLD))

    result: GraphResult | None = None

    for event in stream_graph(query):
        if isinstance(event, NodeStartEvent):
            icon, name, desc = NODE_DISPLAY.get(
                event.node_name,
                ("⚙️", event.node_name.title(), "Processing...")
            )
            print(f"  {icon} {colorize(name, Colors.CYAN)}: {colorize(desc, Colors.DIM)}")

        elif isinstance(event, NodeEndEvent):
            icon, name, _ = NODE_DISPLAY.get(
                event.node_name,
                ("⚙️", event.node_name.title(), "")
            )
            duration = f"{event.duration_ms:.0f}ms"
            print(f"  {colorize('✓', Colors.GREEN)} {name} completed ({colorize(duration, Colors.DIM)})")

        elif isinstance(event, GraphCompleteEvent):
            result = event.result
            total_ms = event.total_duration_ms
            print(f"\n{colorize('✅ Pipeline complete', Colors.GREEN + Colors.BOLD)} ({total_ms:.0f}ms total)\n")

    if result:
        _output_result(result, output_format)
        return 0
    else:
        print("Error: No result produced", file=sys.stderr)
        return 1


def _output_result(result: GraphResult, output_format: str) -> None:
    """Output result in specified format."""
    if output_format == "json":
        format_result_json(result)
    else:
        format_result_pretty(result)


def run_interactive() -> int:
    """Run in interactive REPL mode.

    Returns:
        Exit code (0 for normal exit).
    """
    print(colorize("\n╔══════════════════════════════════════════╗", Colors.CYAN))
    print(colorize("║     Check-It-AI Interactive Mode         ║", Colors.CYAN + Colors.BOLD))
    print(colorize("╚══════════════════════════════════════════╝", Colors.CYAN))
    print()
    print("Type a historical question to fact-check.")
    print("Commands: 'quit' to exit, 'help' for options")
    print(colorize("-" * 44, Colors.DIM))

    while True:
        try:
            query = input(colorize("\n❯ ", Colors.GREEN)).strip()

            if not query:
                continue

            if query.lower() in ("quit", "exit", "q"):
                print(colorize("\nGoodbye! 👋", Colors.CYAN))
                break

            if query.lower() == "help":
                print("\nCommands:")
                print("  quit, exit, q  - Exit interactive mode")
                print("  help           - Show this help")
                print("\nJust type any historical question to fact-check it!")
                continue

            # Run with streaming for interactive mode
            _run_with_streaming(query, "pretty")

        except KeyboardInterrupt:
            print(colorize("\n\nInterrupted. Type 'quit' to exit.", Colors.YELLOW))
        except EOFError:
            print(colorize("\nGoodbye! 👋", Colors.CYAN))
            break

    return 0


# =============================================================================
# Main Entry Point
# =============================================================================

def main(argv: list[str] | None = None) -> int:
    """Main CLI entry point.

    Args:
        argv: Command-line arguments (defaults to sys.argv[1:]).

    Returns:
        Exit code.
    """
    parser = argparse.ArgumentParser(
        prog="check-it-ai",
        description="Check-It-AI: Historical Fact-Checking System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s "When did World War II end?"
  %(prog)s --stream "Was Napoleon actually short?"
  %(prog)s --format json "When did Rome fall?" > result.json
  %(prog)s --interactive
        """,
    )

    parser.add_argument(
        "query",
        nargs="?",
        help="Historical question to fact-check",
    )

    parser.add_argument(
        "-i", "--interactive",
        action="store_true",
        help="Run in interactive mode (REPL)",
    )

    parser.add_argument(
        "-s", "--stream",
        action="store_true",
        help="Show streaming progress as pipeline executes",
    )

    parser.add_argument(
        "-f", "--format",
        choices=["pretty", "json"],
        default="pretty",
        help="Output format (default: pretty)",
    )

    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug output",
    )

    parser.add_argument(
        "--version",
        action="version",
        version="check-it-ai 0.1.0",
    )

    args = parser.parse_args(argv)

    # Determine execution mode
    if args.interactive:
        return run_interactive()
    elif args.query:
        return run_single_query(
            args.query,
            output_format=args.format,
            use_streaming=args.stream,
            debug=args.debug,
        )
    else:
        # No query provided, show help
        parser.print_help()
        return 0


if __name__ == "__main__":
    sys.exit(main())
```

### Package Entry Point

```python
# src/check_it_ai/__main__.py

"""Allow running as: python -m check_it_ai"""

from src.check_it_ai.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
```

### pyproject.toml Addition

```toml
[project.scripts]
check-it-ai = "check_it_ai.cli:main"
```

---

## E. Test Plan

### Unit Tests

| Test ID | Test Name | Description |
|---------|-----------|-------------|
| T01 | `test_build_graph_has_all_nodes` | Verify router, researcher, analyst, writer nodes exist |
| T02 | `test_build_graph_entry_point` | Verify entry point is router |
| T03 | `test_compile_graph_without_checkpointer` | Compile stateless graph |
| T04 | `test_compile_graph_with_checkpointer` | Compile with MemorySaver |
| T05 | `test_route_after_router_fact_check` | Conditional routing returns "researcher" |
| T06 | `test_route_after_router_clarify` | Conditional routing returns END |
| T07 | `test_route_after_router_out_of_scope` | Conditional routing returns END |

### Runner Tests

| Test ID | Test Name | Description |
|---------|-----------|-------------|
| R01 | `test_run_graph_returns_graph_result` | Verify return type |
| R02 | `test_run_graph_fact_check_route` | Full pipeline with mocked search |
| R03 | `test_run_graph_clarify_route` | Verify clarify returns appropriate message |
| R04 | `test_run_graph_out_of_scope_route` | Verify out_of_scope returns appropriate message |
| R05 | `test_run_graph_with_checkpointer` | Test state persistence |
| R06 | `test_arun_graph_async` | Test async execution |
| R07 | `test_stream_graph_events` | Verify streaming yields correct event types |

### CLI Tests

| Test ID | Test Name | Description |
|---------|-----------|-------------|
| C01 | `test_cli_single_query` | Run CLI with query argument |
| C02 | `test_cli_json_output` | Verify --format json works |
| C03 | `test_cli_streaming_output` | Verify --stream shows progress |
| C04 | `test_cli_no_args_shows_help` | Verify help displayed without args |
| C05 | `test_cli_version` | Verify --version works |

### Integration Tests

| Test ID | Test Name | Description |
|---------|-----------|-------------|
| I01 | `test_full_pipeline_with_mocked_search` | End-to-end with mocked Google API |
| I02 | `test_full_pipeline_empty_results` | Graceful handling of no search results |
| I03 | `test_checkpointer_session_persistence` | State persists across invocations |

---

## F. File Structure

### Files to Create

| File Path | Description |
|-----------|-------------|
| `src/check_it_ai/graph/runner.py` | Graph execution utilities (run_graph, stream_graph, etc.) |
| `src/check_it_ai/graph/retry.py` | Retry decorator and utilities |
| `src/check_it_ai/cli.py` | Command-line interface |
| `src/check_it_ai/__main__.py` | Package entry point |
| `tests/graph/test_graph_assembly.py` | Graph assembly tests |
| `tests/graph/test_runner.py` | Runner function tests |
| `tests/test_cli.py` | CLI tests |

### Files to Modify

| File Path | Changes |
|-----------|---------|
| `src/check_it_ai/graph/graph.py` | Replace with new implementation |
| `pyproject.toml` | Add `[project.scripts]` entry |

---

## G. Implementation Order

### Phase 1: Core Graph (Day 1)
1. Create `graph.py` with `build_graph()` and `compile_graph()`
2. Create `runner.py` with `run_graph()` (sync only first)
3. Write unit tests for graph assembly

### Phase 2: Streaming & Async (Day 2)
1. Add `stream_graph()` to runner
2. Add `arun_graph()` and `astream_graph()`
3. Add retry utilities
4. Write streaming tests

### Phase 3: CLI (Day 3)
1. Create `cli.py` with all modes
2. Create `__main__.py`
3. Update `pyproject.toml`
4. Write CLI tests

### Phase 4: Integration & Polish (Day 4)
1. Integration testing with mocked APIs
2. Manual testing and demo preparation
3. Documentation updates

---

## H. Usage Examples

### Single Query (Basic)
```bash
uv run python -m check_it_ai "When did World War II end?"
```

Output:
```
============================================================
Route: FACT_CHECK
============================================================

ANSWER:
----------------------------------------
World War II ended on September 2, 1945, with Japan's formal
surrender aboard the USS Missouri [E1][E2].

Confidence: 92.5%

CITATIONS:
----------------------------------------
  [E1] World War II - Wikipedia
       https://en.wikipedia.org/wiki/World_War_II
  [E2] V-J Day - History.com
       https://www.history.com/topics/v-j-day

============================================================
```

### With Streaming Progress
```bash
uv run python -m check_it_ai --stream "Was Napoleon short?"
```

Output:
```
🚀 Starting fact-check pipeline...

  🔀 Router: Analyzing query...
  ✓ Router completed (45ms)
  🔍 Researcher: Searching for evidence...
  ✓ Researcher completed (1,234ms)
  🔬 Analyst: Evaluating evidence...
  ✓ Analyst completed (892ms)
  ✍️ Writer: Generating answer...
  ✓ Writer completed (1,567ms)

✅ Pipeline complete (3,738ms total)

============================================================
Route: FACT_CHECK
============================================================

ANSWER:
----------------------------------------
Napoleon Bonaparte was not unusually short for his time...
```

### Interactive Mode
```bash
uv run python -m check_it_ai --interactive
```

Output:
```
╔══════════════════════════════════════════╗
║     Check-It-AI Interactive Mode         ║
╚══════════════════════════════════════════╝

Type a historical question to fact-check.
Commands: 'quit' to exit, 'help' for options
--------------------------------------------

❯ When did the Roman Empire fall?

🚀 Starting fact-check pipeline...
  ...

❯ quit
Goodbye! 👋
```

### JSON Output (for scripting)
```bash
uv run python -m check_it_ai --format json "When did Rome fall?" | jq .confidence
# Output: 0.85
```

---

## I. Design Decisions Summary

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Graph framework | LangGraph StateGraph | Project standard, supports streaming/checkpointing |
| Checkpointing backend | MemorySaver | Simple for MVP, can swap to SQLite/Redis later |
| Streaming mode | `stream_mode="updates"` | Shows node-by-node progress |
| CLI library | argparse | Standard library, no extra dependency |
| Output formatting | Custom with ANSI colors | Professional demo appearance |
| Error handling | Graceful fallbacks | Never crash during demo |
| Retry strategy | 1 retry with 1s delay | Balance between reliability and latency |

---

## J. Success Criteria

| Criteria | Target | Verification |
|----------|--------|--------------|
| Graph compiles | No errors | `compile_graph()` succeeds |
| All routes work | 3/3 routes | Unit tests pass |
| Streaming works | Events yielded | Stream test shows all event types |
| Async works | No blocking | `arun_graph()` returns correctly |
| CLI runs | All modes | Manual testing of each mode |
| Demo ready | Looks professional | Streaming output with colors |
| Tests pass | 100% | `uv run pytest` green |

---

## K. Open Questions (Resolved)

1. **Fact Analyst Integration**: ✅ **RESOLVED** - AH-07 merged and integrated. Uses same node interface (`state: AgentState -> dict`).

2. **Session Management**: Deferred to future enhancement. CLI supports `--interactive` mode for now.

3. **LangSmith Tracing**: Deferred to production phase.

---

**End of AH-09 Design Document**

This design provides a complete blueprint for assembling the LangGraph pipeline with streaming, checkpointing, and async support, plus a professional CLI for demonstrations.
