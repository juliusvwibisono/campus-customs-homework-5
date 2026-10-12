"""FastAPI routes for the Campus Customs dashboard."""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path
from threading import Lock
from typing import Any, Literal

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field


# This supports the assignment's launch command from backend/: uvicorn main:app.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.mcp_client import MCPGateway  # noqa: E402
from backend.models import TeamRunRequest  # noqa: E402
from backend.team import run_team  # noqa: E402


app = FastAPI(title="Campus Customs Operations API", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000", "http://localhost:8000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

ORIGINAL_DATABASE = PROJECT_ROOT / "data" / "campus_customs.db"
WORKING_DATABASE = PROJECT_ROOT / "data" / "campus_customs_new.db"
AUDIT_PATH = PROJECT_ROOT / "output" / "audit_trail.json"
RESET_LOCK = Lock()


class RunTicketRequest(BaseModel):
    instruction: str = Field(
        default="Review this ticket, delegate only to the specialists needed, and record the next safe action."
    )
    max_steps: int = Field(default=24, ge=1, le=50)
    max_delegation_depth: int = Field(default=3, ge=0, le=5)


class PaymentApprovalRequest(BaseModel):
    kind: Literal["invoice", "rent"]
    reference_id: int = Field(gt=0)
    amount: float = Field(gt=0)
    account: str = "checking"
    approved_by: str = Field(min_length=1)


class PurchaseApprovalRequest(BaseModel):
    invoice_id: int = Field(gt=0)
    amount: float = Field(gt=0)
    account: str = "checking"
    approved_by: str = Field(min_length=1)


async def _mcp_call(tool_name: str, arguments: dict[str, Any] | None = None) -> Any:
    async with MCPGateway(PROJECT_ROOT) as mcp:
        return await mcp.call(tool_name, arguments or {})


@app.get("/", tags=["system"])
async def root() -> dict[str, str]:
    return {"service": "Campus Customs Operations API", "status": "ok"}


@app.get("/api/tickets", tags=["tickets"])
async def tickets() -> list[dict[str, Any]]:
    """Return all three tickets and their current open/resolved status."""
    try:
        return await _mcp_call("list_tickets")
    except Exception as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@app.get("/api/tickets/{ticket_id}/context", tags=["tickets"])
async def ticket_context(ticket_id: int) -> dict[str, Any]:
    """Return the selected ticket's linked MCP records for the dashboard and approval card."""
    if ticket_id not in {101, 102, 103}:
        raise HTTPException(status_code=404, detail=f"Unknown ticket id: {ticket_id}")
    try:
        return await _mcp_call("get_ticket_context", {"ticket_id": ticket_id})
    except Exception as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@app.post("/api/tickets/{ticket_id}/run", tags=["agents"])
async def run_ticket(ticket_id: int, request: RunTicketRequest | None = None) -> dict[str, Any]:
    """Run Boss and the selectively delegated agent team for one ticket."""
    if ticket_id not in {101, 102, 103}:
        raise HTTPException(status_code=404, detail=f"Unknown ticket id: {ticket_id}")
    request = request or RunTicketRequest()
    team_request = TeamRunRequest(
        prompt=f"Ticket {ticket_id}: {request.instruction}",
        ticket_id=ticket_id,
        max_steps=request.max_steps,
        max_delegation_depth=request.max_delegation_depth,
    )
    try:
        result = await run_team(team_request)
        if result.status == "resolved":
            current = await _mcp_call("get_ticket_context", {"ticket_id": ticket_id})
            if current["ticket"]["status"] != "resolved":
                await _mcp_call(
                    "update_ticket_status",
                    {
                        "ticket_id": ticket_id,
                        "status": "resolved",
                        "note": result.summary,
                        "updated_by": "Boss",
                    },
                )
        return {"ticket_id": ticket_id, "result": result.model_dump()}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get("/api/events", tags=["events"])
async def events(limit: int = Query(default=100, ge=1, le=500)) -> list[dict[str, Any]]:
    """Return recent agent/delegation/MCP events for dashboard refreshes."""
    if not AUDIT_PATH.exists():
        return []
    try:
        records = json.loads(AUDIT_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=500, detail="Audit trail is not valid JSON") from exc
    if not isinstance(records, list):
        raise HTTPException(status_code=500, detail="Audit trail must contain a JSON list")
    return list(reversed(records[-limit:]))


@app.post("/api/approvals/payment", tags=["approvals"])
async def approve_payment(request: PaymentApprovalRequest) -> dict[str, Any]:
    """Apply a human-approved invoice or rent payment through the MCP guardrails."""
    try:
        result = await _mcp_call(
            "record_approved_payment",
            {
                "kind": request.kind,
                "ref_id": request.reference_id,
                "amount": request.amount,
                "account": request.account,
                "approved_by": request.approved_by,
            },
        )
        return {"approved": True, "result": result}
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/approvals/purchase", tags=["approvals"])
async def approve_purchase(request: PurchaseApprovalRequest) -> dict[str, Any]:
    """Approve payment of a recorded purchase invoice; no unmodeled purchase is invented."""
    try:
        result = await _mcp_call(
            "record_approved_payment",
            {
                "kind": "invoice",
                "ref_id": request.invoice_id,
                "amount": request.amount,
                "account": request.account,
                "approved_by": request.approved_by,
            },
        )
        return {"approved": True, "result": result}
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/api/cash", tags=["cash"])
async def cash(account: str = "checking") -> dict[str, Any]:
    """Return the current checking balance from the MCP cash tool."""
    try:
        return await _mcp_call("get_cash_balance", {"account": account})
    except Exception as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@app.post("/api/reset", tags=["system"])
async def reset_database() -> dict[str, str]:
    """Restore the working database from the untouched original database."""
    if not ORIGINAL_DATABASE.is_file():
        raise HTTPException(status_code=500, detail="Original database is missing")
    try:
        with RESET_LOCK:
            shutil.copy2(ORIGINAL_DATABASE, WORKING_DATABASE)
    except OSError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return {"status": "reset", "database": str(WORKING_DATABASE.relative_to(PROJECT_ROOT))}
