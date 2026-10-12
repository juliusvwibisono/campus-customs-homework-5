"""Boss agent."""

from typing import Any

from pydantic_ai import Agent

from ..models import AgentDecision, TeamDeps
from .factory import build_role_agent


def build_boss_agent(model: Any) -> Agent[TeamDeps, AgentDecision]:
    return build_role_agent(
        model,
        "Boss",
        "boss.md",
        "Final routing and decision agent for Campus Customs tickets.",
    )
