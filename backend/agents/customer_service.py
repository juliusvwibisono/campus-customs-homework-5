"""Customer Service agent."""

from typing import Any

from pydantic_ai import Agent

from ..models import AgentDecision, TeamDeps
from .factory import build_role_agent


def build_customer_service_agent(model: Any) -> Agent[TeamDeps, AgentDecision]:
    return build_role_agent(
        model,
        "Customer Service",
        "customer_service.md",
        "Customer and organization message-drafting specialist.",
    )
