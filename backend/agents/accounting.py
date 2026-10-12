"""Accounting agent."""

from typing import Any

from pydantic_ai import Agent

from ..models import AgentDecision, TeamDeps
from .factory import build_role_agent


def build_accounting_agent(model: Any) -> Agent[TeamDeps, AgentDecision]:
    return build_role_agent(
        model,
        "Accounting",
        "accounting.md",
        "Cash, invoice, margin, and human-payment-approval specialist.",
    )
