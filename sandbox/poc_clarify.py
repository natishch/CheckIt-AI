# src/check_it_ai/graph/state.py
from pydantic import BaseModel, Field
from typing import Any, Literal, Optional

from src.check_it_ai.types.clarify import ClarifyRequest  # adjust import if needed

AgentRoute = Literal["fact_check", "clarify", "out_of_scope"]


class AgentState(BaseModel):
    user_query: str = ""
    route: Optional[AgentRoute] = None
    run_metadata: dict[str, Any] = Field(default_factory=dict)

    clarify_request: Optional[ClarifyRequest] = None
    ...
