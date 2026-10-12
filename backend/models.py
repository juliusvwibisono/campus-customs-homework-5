"""Shared types passed between the Campus Customs agents."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

from pydantic import BaseModel, Field


AgentRole = Literal["Boss", "Inventory", "Accounting", "Facilities", "Customer Service"]
TicketStatus = Literal["open", "in_progress", "waiting_approval", "resolved"]


class Evidence(BaseModel):
    source: str
    detail: str


class AgentDecision(BaseModel):
    summary: str = Field(min_length=1)
    status: TicketStatus = "in_progress"
    next_steps: list[str] = Field(default_factory=list)
    needs_human_approval: bool = False
    evidence: list[Evidence] = Field(default_factory=list)


class DelegationResult(BaseModel):
    delegated_to: AgentRole
    summary: str
    status: TicketStatus = "in_progress"
    needs_human_approval: bool = False
    evidence: list[Evidence] = Field(default_factory=list)


@dataclass
class TeamDeps:
    """Runtime dependencies supplied to every PydanticAI agent."""

    runtime: Any
    role: AgentRole
    ticket_id: int | None = None
    delegation_depth: int = 0


class TeamRunRequest(BaseModel):
    prompt: str
    ticket_id: int | None = None
    max_steps: int = Field(default=24, ge=1, le=50)
    max_delegation_depth: int = Field(default=3, ge=0, le=5)
