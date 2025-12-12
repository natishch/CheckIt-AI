from __future__ import annotations

import argparse
import json
from typing import Any

from src.check_it_ai.graph.nodes.router import router_node
from src.check_it_ai.graph.state import AgentState


def _print_human_readable(route: str | None, meta: dict[str, Any]) -> None:
    print("=== Router Decision ===")
    print(f"Route       : {route}")
    print(f"Reason code : {meta.get('reason_code')}")
    print(f"Reason text : {meta.get('reason_text')}")
    print()

    features = meta.get("features") or {}
    if features:
        print("=== Features ===")
        for k, v in features.items():
            print(f"{k:20}: {v}")
        print()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Inspect router decisions for sample queries.",
    )
    parser.add_argument(
        "query",
        nargs="*",
        help="User query to route (if omitted, will prompt interactively).",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print full router metadata as JSON.",
    )

    args = parser.parse_args()

    if args.query:
        query = " ".join(args.query)
    else:
        try:
            query = input("Enter query: ").strip()
        except EOFError:
            query = ""

    state = AgentState(user_query=query)
    state = router_node(state)

    meta = state.run_metadata.get("router", {})

    _print_human_readable(state.route, meta)

    if args.json:
        print("=== Router metadata (JSON) ===")
        print(json.dumps(meta, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
"""
uv run python -m agentic_historian.debug.router "When did the Berlin Wall fall?"
uv run python -m agentic_historian.debug.router "write a poem about WW2" --json
uv run python -m agentic_historian.debug.router
# then type the query interactively
"""
