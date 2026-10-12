"""Full-connectivity PydanticAI team runtime."""

from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Any

from pydantic_ai import UsageLimits

from .agents import (
    build_accounting_agent,
    build_boss_agent,
    build_customer_service_agent,
    build_facilities_agent,
    build_inventory_agent,
)
from .audit import AuditTrail
from .config import create_agent_model
from .mcp_client import MCPGateway
from .models import AgentDecision, AgentRole, DelegationResult, TeamDeps, TeamRunRequest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
AUDIT_PATH = PROJECT_ROOT / "output" / "audit_trail.json"
ALL_ROLES: tuple[AgentRole, ...] = (
    "Boss",
    "Inventory",
    "Accounting",
    "Facilities",
    "Customer Service",
)


class TeamRuntime:
    def __init__(
        self,
        mcp: MCPGateway,
        audit: AuditTrail,
        agents: dict[AgentRole, Any],
        *,
        max_steps: int,
        max_delegation_depth: int,
    ):
        self.mcp = mcp
        self.audit = audit
        self.agents = agents
        self.max_steps = max_steps
        self.max_delegation_depth = max_delegation_depth
        self.steps = 0

    async def call_mcp(self, deps: TeamDeps, tool_name: str, arguments: dict[str, Any]) -> Any:
        self.steps += 1
        if self.steps > self.max_steps:
            self.audit.append(
                "limit_blocked",
                agent=deps.role,
                ticket_id=deps.ticket_id,
                action="mcp_call",
                tool_name=tool_name,
                detail="maximum team steps reached",
            )
            raise RuntimeError("Team step limit reached")

        self.audit.append(
            "mcp_tool_started",
            agent=deps.role,
            ticket_id=deps.ticket_id,
            action="mcp_call",
            tool_name=tool_name,
            arguments=arguments,
        )
        try:
            result = await self.mcp.call(tool_name, arguments)
        except Exception as exc:
            self.audit.append(
                "mcp_tool_failed",
                agent=deps.role,
                ticket_id=deps.ticket_id,
                action="mcp_call",
                tool_name=tool_name,
                error=str(exc),
            )
            raise
        self.audit.append(
            "mcp_tool_completed",
            agent=deps.role,
            ticket_id=deps.ticket_id,
            action="mcp_call",
            tool_name=tool_name,
            output_preview=json.dumps(result, default=str)[:2000],
        )
        return result

    async def delegate(
        self,
        *,
        caller: AgentRole,
        target: AgentRole,
        task: str,
        ticket_id: int | None,
        depth: int,
    ) -> DelegationResult:
        self.steps += 1
        if target not in ALL_ROLES:
            raise ValueError(f"Unknown agent role: {target}")
        if depth > self.max_delegation_depth:
            self.audit.append(
                "delegation_blocked",
                agent=caller,
                delegated_to=target,
                ticket_id=ticket_id,
                action="delegate",
                detail="maximum delegation depth reached",
            )
            return DelegationResult(
                delegated_to=target,
                summary="Delegation stopped at the configured depth limit.",
                status="waiting_approval",
            )
        if self.steps > self.max_steps:
            self.audit.append(
                "limit_blocked",
                agent=caller,
                delegated_to=target,
                ticket_id=ticket_id,
                action="delegate",
                detail="maximum team steps reached",
            )
            return DelegationResult(
                delegated_to=target,
                summary="Delegation stopped at the configured team-step limit.",
                status="waiting_approval",
            )

        self.audit.append(
            "delegation_started",
            agent=caller,
            delegated_to=target,
            ticket_id=ticket_id,
            action="delegate",
            task=task,
            depth=depth,
        )
        deps = TeamDeps(
            runtime=self,
            role=target,
            ticket_id=ticket_id,
            delegation_depth=depth,
        )
        try:
            result = await self.agents[target].run(
                task,
                deps=deps,
                usage_limits=UsageLimits(
                    request_limit=8,
                    tool_calls_limit=12,
                    output_tokens_limit=900,
                ),
            )
            output = result.output
            if not isinstance(output, AgentDecision):
                raise TypeError(f"{target} returned an unexpected output type")
            response = DelegationResult(
                delegated_to=target,
                summary=output.summary,
                status=output.status,
                needs_human_approval=output.needs_human_approval,
                evidence=output.evidence,
            )
            self.audit.append(
                "delegation_completed",
                agent=caller,
                delegated_to=target,
                ticket_id=ticket_id,
                action="delegate",
                status=response.status,
                summary=response.summary,
                needs_human_approval=response.needs_human_approval,
            )
            return response
        except Exception as exc:
            self.audit.append(
                "delegation_failed",
                agent=caller,
                delegated_to=target,
                ticket_id=ticket_id,
                action="delegate",
                error=str(exc),
            )
            raise


def build_agents(model: Any) -> dict[AgentRole, Any]:
    """Build all five roles with the same Portkey-backed gpt-6-luna model."""
    return {
        "Boss": build_boss_agent(model),
        "Inventory": build_inventory_agent(model),
        "Accounting": build_accounting_agent(model),
        "Facilities": build_facilities_agent(model),
        "Customer Service": build_customer_service_agent(model),
    }


async def run_team(request: TeamRunRequest) -> AgentDecision | DelegationResult:
    """Run Boss over the team and append every step to the persistent audit trail."""
    run_id = str(uuid.uuid4())
    audit = AuditTrail(AUDIT_PATH, run_id)
    audit.append(
        "team_run_started",
        agent="Boss",
        ticket_id=request.ticket_id,
        action="run_team",
        prompt=request.prompt,
        max_steps=request.max_steps,
        max_delegation_depth=request.max_delegation_depth,
    )

    model = create_agent_model()
    agents = build_agents(model)
    async with MCPGateway(PROJECT_ROOT) as mcp:
        runtime = TeamRuntime(
            mcp,
            audit,
            agents,
            max_steps=request.max_steps,
            max_delegation_depth=request.max_delegation_depth,
        )
        result = await runtime.delegate(
            caller="Boss",
            target="Boss",
            task=request.prompt,
            ticket_id=request.ticket_id,
            depth=0,
        )

    audit.append(
        "team_run_completed",
        agent="Boss",
        ticket_id=request.ticket_id,
        action="run_team",
        status=result.status,
        summary=result.summary,
        needs_human_approval=result.needs_human_approval,
    )
    return result
