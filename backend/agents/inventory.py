"""Inventory agent."""

from typing import Any

from pydantic_ai import Agent

from ..models import AgentDecision, TeamDeps
from .factory import build_role_agent


def build_inventory_agent(model: Any) -> Agent[TeamDeps, AgentDecision]:
    return build_role_agent(
        model,
        "Inventory",
        "inventory.md",
        "SKU, size, stock, shortage, and vendor-restocking specialist.",
    )
