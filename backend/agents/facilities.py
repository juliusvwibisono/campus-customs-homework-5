"""Facilities agent."""

from typing import Any

from pydantic_ai import Agent

from ..models import AgentDecision, TeamDeps
from .factory import build_role_agent


def build_facilities_agent(model: Any) -> Agent[TeamDeps, AgentDecision]:
    return build_role_agent(
        model,
        "Facilities",
        "facilities.md",
        "Lease, rent, shop-space, and landlord-draft specialist.",
    )
