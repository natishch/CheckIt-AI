"""Pydantic state definitions for LangGraph."""

from typing import Literal

from pydantic import BaseModel


class GraphState(BaseModel):
    """Shared state for the agentic workflow."""

    user_query: str = ""
    route: Literal["fact_check", "clarify", "out_of_scope"] = "fact_check"
    final_answer: str = ""
