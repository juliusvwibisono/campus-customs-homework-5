"""Shared PydanticAI tools installed on every role for full connectivity."""

from __future__ import annotations

from typing import Any

from pydantic_ai import Agent, RunContext

from ..models import AgentRole, TeamDeps


def install_common_tools(agent: Agent[TeamDeps, Any], role: AgentRole) -> None:
    """Give every agent all delegation routes and the MCP boundary tools."""

    def add_delegate(target_role: AgentRole) -> None:
        async def delegate(
            ctx: RunContext[TeamDeps], task: str, ticket_id: int | None = None
        ):
            return await ctx.deps.runtime.delegate(
                caller=role,
                target=target_role,
                task=task,
                ticket_id=ticket_id or ctx.deps.ticket_id,
                depth=ctx.deps.delegation_depth + 1,
            )

        delegate.__name__ = f"delegate_to_{target_role.lower().replace(' ', '_')}"
        delegate.__doc__ = f"Delegate a focused task to {target_role}."
        agent.tool(delegate)

    for target in ("Boss", "Inventory", "Accounting", "Facilities", "Customer Service"):
        add_delegate(target)  # type: ignore[arg-type]

    @agent.tool
    async def list_open_tickets(ctx: RunContext[TeamDeps]) -> Any:
        """Read the current open work queue from MCP."""
        return await ctx.deps.runtime.call_mcp(ctx.deps, "list_open_tickets", {})

    @agent.tool
    async def list_tickets(ctx: RunContext[TeamDeps]) -> Any:
        """Read all ticket statuses from MCP."""
        return await ctx.deps.runtime.call_mcp(ctx.deps, "list_tickets", {})

    @agent.tool
    async def get_cash_balance(
        ctx: RunContext[TeamDeps], account: str = "checking"
    ) -> Any:
        """Read one cash-account balance from MCP."""
        return await ctx.deps.runtime.call_mcp(
            ctx.deps, "get_cash_balance", {"account": account}
        )

    @agent.tool
    async def inspect_inventory(
        ctx: RunContext[TeamDeps],
        sku: str,
        size: str,
        requested_qty: int | None = None,
    ) -> Any:
        """Read exact SKU/size inventory and pricing from MCP."""
        return await ctx.deps.runtime.call_mcp(
            ctx.deps,
            "inspect_inventory",
            {"sku": sku, "size": size, "requested_qty": requested_qty},
        )

    @agent.tool
    async def get_ticket_context(ctx: RunContext[TeamDeps], ticket_id: int) -> Any:
        """Read one ticket and its linked shop records from MCP."""
        return await ctx.deps.runtime.call_mcp(
            ctx.deps, "get_ticket_context", {"ticket_id": ticket_id}
        )

    @agent.tool
    async def get_restock_options(
        ctx: RunContext[TeamDeps], sku: str, size: str, requested_qty: int
    ) -> Any:
        """Read stock, vendor lead times, and unpaid-invoice shipping blocks from MCP."""
        return await ctx.deps.runtime.call_mcp(
            ctx.deps,
            "get_restock_options",
            {"sku": sku, "size": size, "requested_qty": requested_qty},
        )

    @agent.tool
    async def append_ticket_note(
        ctx: RunContext[TeamDeps], ticket_id: int, note: str, author: str
    ) -> Any:
        """Put a draft or review note on the ticket board through MCP."""
        return await ctx.deps.runtime.call_mcp(
            ctx.deps,
            "append_ticket_note",
            {"ticket_id": ticket_id, "note": note, "author": author},
        )

    @agent.tool
    async def update_ticket_status(
        ctx: RunContext[TeamDeps],
        ticket_id: int,
        status: str,
        note: str,
        updated_by: str,
    ) -> Any:
        """Update a ticket's board status through MCP."""
        return await ctx.deps.runtime.call_mcp(
            ctx.deps,
            "update_ticket_status",
            {
                "ticket_id": ticket_id,
                "status": status,
                "note": note,
                "updated_by": updated_by,
            },
        )
