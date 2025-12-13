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
import os
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


class Colors:
    """ANSI color codes for terminal output."""

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
    return (
        hasattr(sys.stdout, "isatty")
        and sys.stdout.isatty()
        and os.environ.get("TERM") != "dumb"
        and os.environ.get("NO_COLOR") is None
    )


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
    "writer": ("✍️ ", "Writer", "Generating answer..."),
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
        if conf_pct >= 70:
            conf_color = Colors.GREEN
        elif conf_pct >= 40:
            conf_color = Colors.YELLOW
        else:
            conf_color = Colors.RED
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
            print(
                colorize(f"  Total time: {meta['total_time_seconds']:.2f}s", Colors.DIM), file=file
            )
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
                event.node_name, ("⚙️ ", event.node_name.title(), "Processing...")
            )
            print(f"  {icon} {colorize(name, Colors.CYAN)}: {colorize(desc, Colors.DIM)}")

        elif isinstance(event, NodeEndEvent):
            icon, name, _ = NODE_DISPLAY.get(event.node_name, ("⚙️ ", event.node_name.title(), ""))
            duration = f"{event.duration_ms:.0f}ms"
            print(
                f"  {colorize('✓', Colors.GREEN)} {name} completed ({colorize(duration, Colors.DIM)})"
            )

        elif isinstance(event, GraphCompleteEvent):
            result = event.result
            total_ms = event.total_duration_ms
            print(
                f"\n{colorize('✅ Pipeline complete', Colors.GREEN + Colors.BOLD)} ({total_ms:.0f}ms total)\n"
            )

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
        "-i",
        "--interactive",
        action="store_true",
        help="Run in interactive mode (REPL)",
    )

    parser.add_argument(
        "-s",
        "--stream",
        action="store_true",
        help="Show streaming progress as pipeline executes",
    )

    parser.add_argument(
        "-f",
        "--format",
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
