# src/agentic_historian/app/streamlit_app.py (sketch)
from __future__ import annotations

import streamlit as st

from src.check_it_ai.config import settings
from src.check_it_ai.graph.graph import run_graph

SETTINGS=settings
def render_router_debug(state) -> None:
    if not SETTINGS.router_debug:
        return
    if "router" not in state.run_metadata:
        return

    with st.expander("Router debug"):
        st.json(state.run_metadata["router"])


def main() -> None:
    st.set_page_config(page_title="Agentic Historian", layout="wide")
    st.title("Agentic Historian")

    if "messages" not in st.session_state:
        st.session_state.messages = []

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    user_query = st.chat_input("Ask a historical question...")
    if not user_query:
        return

    st.session_state.messages.append({"role": "user", "content": user_query})

    # Run the graph
    state = run_graph(user_query)

    # Branch on route
    if state.route == "clarify" and state.clarify_request:
        cr = state.clarify_request
        with st.chat_message("assistant"):
            st.markdown("### I need a bit more detail")
            st.write(cr.message)

            for field in cr.fields:
                label_map = {
                    "claim": "Claim",
                    "entity": "Person / entity",
                    "event": "Event",
                    "time_period": "Time period",
                    "location": "Location",
                }
                label = label_map.get(field.key, field.key.capitalize())

                st.markdown(f"**{label}**")
                st.write(field.question)
                if field.hint:
                    st.caption(field.hint)

            render_router_debug(state)

        st.session_state.messages.append(
            {
                "role": "assistant",
                "content": cr.message,
            }
        )

    elif state.route == "out_of_scope":
        with st.chat_message("assistant"):
            st.markdown("### Out of scope")
            st.write(
                "This assistant is focused on historical fact-checking. Your last request appears "
                "to be outside that scope (e.g., coding, generic content generation).",
            )

            render_router_debug(state)

        st.session_state.messages.append(
            {
                "role": "assistant",
                "content": "Your last request seems outside the historical fact-checking scope.",
            }
        )

    else:
        # Normal fact_check flow
        # Here we assume the writer node populated `state.final_answer`
        # and that `state.evidence_bundle` is an EvidenceBundle instance.
        final_answer = getattr(state, "final_answer", None)
        evidence_bundle = getattr(state, "evidence_bundle", None)
        # inside Streamlit fact_check branch (from previous message)
        writer_output = state.writer_output
        evidence_bundle = getattr(state, "evidence_bundle", None)

        with st.chat_message("assistant"):
            if writer_output:
                st.markdown("### Answer")
                st.markdown(writer_output.answer)

                st.markdown("#### Confidence")
                st.write(f"{writer_output.confidence:.2f}")

                st.markdown("#### Limitations")
                st.write(writer_output.limitations or "Not specified.")

            else:
                st.write("I processed your query, but no final answer was generated.")

            if evidence_bundle:
                st.markdown("### Evidence")
                for item in evidence_bundle.evidence_items:
                    with st.expander(f"{item.id} — {item.title}"):
                        st.write(item.snippet)
                        st.write(f"[Open source]({item.url})")

                st.markdown("#### Verdict")
                st.write(f"Overall verdict: **{evidence_bundle.overall_verdict}**")

            writer_meta = state.run_metadata.get("writer", {})
            if writer_meta:
                st.markdown("#### Answer metadata")
                st.json(writer_meta)

            # router debug expander, as defined earlier
            render_router_debug(state)


        st.session_state.messages.append(
            {
                "role": "assistant",
                "content": final_answer or "",
            }
        )


if __name__ == "__main__":
    main()
