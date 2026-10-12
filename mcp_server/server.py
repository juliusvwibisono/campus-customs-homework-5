"""Read-only MCP tools for the Campus Customs working database."""

from __future__ import annotations

import sqlite3
from contextlib import closing
from pathlib import Path
from threading import Lock
from typing import Any

from fastmcp import FastMCP


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATABASE_PATH = PROJECT_ROOT / "data" / "campus_customs_new.db"
DATABASE_URI = DATABASE_PATH.as_uri() + "?mode=ro"
WRITE_LOCK = Lock()
VALID_TICKET_STATUSES = {"open", "in_progress", "waiting_approval", "resolved"}
AGENT_IDENTITIES = {"boss", "inventory", "accounting", "facilities", "customer service"}

mcp = FastMCP("Campus Customs MCP")


def _connect(*, read_only: bool = True) -> sqlite3.Connection:
    """Open the working database, read-only unless a guarded tool needs to write."""
    if not DATABASE_PATH.is_file():
        raise FileNotFoundError(f"Database not found: {DATABASE_PATH}")

    if read_only:
        connection = sqlite3.connect(DATABASE_URI, uri=True)
    else:
        connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def _record(row: sqlite3.Row | None) -> dict[str, Any] | None:
    return dict(row) if row is not None else None


@mcp.tool()
def list_open_tickets() -> list[dict[str, Any]]:
    """Return every ticket whose status is open, in ticket order."""
    with closing(_connect()) as connection:
        rows = connection.execute(
            """
            SELECT id, type, requester, subject, sku, size, qty,
                   lease_id, invoice_id, status, notes, created_at
            FROM tickets
            WHERE status = 'open'
            ORDER BY id
            """
        ).fetchall()
    return [dict(row) for row in rows]


@mcp.tool()
def list_tickets() -> list[dict[str, Any]]:
    """Return all tickets, including tickets already resolved."""
    with closing(_connect()) as connection:
        rows = connection.execute(
            """
            SELECT id, type, requester, subject, sku, size, qty,
                   lease_id, invoice_id, status, notes, created_at
            FROM tickets
            ORDER BY id
            """
        ).fetchall()
    return [dict(row) for row in rows]


@mcp.tool()
def get_cash_balance(account: str = "checking") -> dict[str, Any]:
    """Return the current balance and date for one cash account."""
    with closing(_connect()) as connection:
        row = connection.execute(
            "SELECT * FROM cash_accounts WHERE name = ?", (account,)
        ).fetchone()
    if row is None:
        raise LookupError(f"No cash account found named {account!r}")
    return dict(row)


@mcp.tool()
def inspect_inventory(
    sku: str,
    size: str,
    requested_qty: int | None = None,
) -> dict[str, Any]:
    """Look up stock for an exact SKU and size, with optional shortage math."""
    with closing(_connect()) as connection:
        row = connection.execute(
            """
            SELECT i.sku, i.name, i.size, i.qty, i.location,
                   p.unit_cost, p.list_price
            FROM inventory AS i
            LEFT JOIN pricing AS p ON p.sku = i.sku
            WHERE i.sku = ? AND i.size = ?
            """,
            (sku, size),
        ).fetchone()

    if row is None:
        raise LookupError(f"No inventory record found for SKU {sku!r}, size {size!r}")

    result = dict(row)
    if requested_qty is not None:
        if requested_qty < 0:
            raise ValueError("requested_qty cannot be negative")
        result["requested_qty"] = requested_qty
        result["shortfall"] = max(requested_qty - result["qty"], 0)
    return result


@mcp.tool()
def get_ticket_context(ticket_id: int) -> dict[str, Any]:
    """Return a ticket and only the database records linked to its request."""
    with closing(_connect()) as connection:
        ticket = connection.execute(
            "SELECT * FROM tickets WHERE id = ?", (ticket_id,)
        ).fetchone()
        if ticket is None:
            raise LookupError(f"No ticket found with id {ticket_id}")

        ticket_data = dict(ticket)
        lease = None
        if ticket["lease_id"] is not None:
            lease = connection.execute(
                "SELECT * FROM leases WHERE id = ?", (ticket["lease_id"],)
            ).fetchone()

        invoice = None
        vendor = None
        if ticket["invoice_id"] is not None:
            invoice = connection.execute(
                "SELECT * FROM invoices WHERE id = ?", (ticket["invoice_id"],)
            ).fetchone()
            if invoice is not None:
                vendor = connection.execute(
                    "SELECT * FROM vendors WHERE id = ?", (invoice["vendor_id"],)
                ).fetchone()

        inventory = None
        pricing = None
        if ticket["sku"] is not None and ticket["size"] is not None:
            inventory = connection.execute(
                """
                SELECT * FROM inventory
                WHERE sku = ? AND size = ?
                """,
                (ticket["sku"], ticket["size"]),
            ).fetchone()
        if ticket["sku"] is not None:
            pricing = connection.execute(
                "SELECT * FROM pricing WHERE sku = ?", (ticket["sku"],)
            ).fetchone()

        shop_date = connection.execute("SELECT * FROM desk LIMIT 1").fetchone()
        cash_accounts = connection.execute("SELECT * FROM cash_accounts").fetchall()
        payments = connection.execute(
            "SELECT * FROM payments WHERE ref_id = ? ORDER BY id", (ticket_id,)
        ).fetchall()

        linked_ref = ticket["invoice_id"] or ticket["lease_id"]
        if linked_ref is not None and linked_ref != ticket_id:
            payments = connection.execute(
                "SELECT * FROM payments WHERE ref_id = ? ORDER BY id", (linked_ref,)
            ).fetchall()

    return {
        "ticket": ticket_data,
        "lease": _record(lease),
        "invoice": _record(invoice),
        "vendor": _record(vendor),
        "inventory": _record(inventory),
        "pricing": _record(pricing),
        "shop": {
            "desk": _record(shop_date),
            "cash_accounts": [dict(row) for row in cash_accounts],
        },
        "payments": [dict(row) for row in payments],
    }


@mcp.tool()
def get_restock_options(
    sku: str,
    size: str,
    requested_qty: int,
) -> dict[str, Any]:
    """Return database-backed stock, pricing, vendors, and invoice blocks for restocking."""
    if requested_qty <= 0:
        raise ValueError("requested_qty must be greater than zero")

    with closing(_connect()) as connection:
        inventory = connection.execute(
            "SELECT * FROM inventory WHERE sku = ? AND size = ?", (sku, size)
        ).fetchone()
        if inventory is None:
            raise LookupError(f"No inventory record found for SKU {sku!r}, size {size!r}")

        pricing = connection.execute(
            "SELECT * FROM pricing WHERE sku = ?", (sku,)
        ).fetchone()
        vendors = connection.execute("SELECT * FROM vendors ORDER BY id").fetchall()
        open_invoices = connection.execute(
            """
            SELECT i.id, i.vendor_id, i.amount, i.due_date, i.status, i.description
            FROM invoices AS i
            WHERE i.status = 'open'
            ORDER BY i.id
            """
        ).fetchall()

    invoices_by_vendor: dict[int, list[dict[str, Any]]] = {}
    for invoice in open_invoices:
        invoices_by_vendor.setdefault(invoice["vendor_id"], []).append(dict(invoice))

    vendor_options = []
    for vendor in vendors:
        vendor_data = dict(vendor)
        vendor_data["open_unpaid_invoices"] = invoices_by_vendor.get(vendor["id"], [])
        vendor_data["can_ship"] = not vendor_data["open_unpaid_invoices"]
        vendor_options.append(vendor_data)

    return {
        "item": dict(inventory),
        "pricing": _record(pricing),
        "requested_qty": requested_qty,
        "shortfall": max(requested_qty - inventory["qty"], 0),
        "vendors": vendor_options,
    }


@mcp.tool()
def append_ticket_note(ticket_id: int, note: str, author: str) -> dict[str, Any]:
    """Append an agent's draft or review note to a ticket; this never contacts anyone."""
    if not note.strip():
        raise ValueError("note cannot be empty")
    if not author.strip():
        raise ValueError("author cannot be empty")

    with WRITE_LOCK, closing(_connect(read_only=False)) as connection:
        ticket = connection.execute(
            "SELECT id, notes FROM tickets WHERE id = ?", (ticket_id,)
        ).fetchone()
        if ticket is None:
            raise LookupError(f"No ticket found with id {ticket_id}")
        shop_date = connection.execute("SELECT date_today FROM desk LIMIT 1").fetchone()
        stamped_note = f"[{shop_date['date_today']}] {author}: {note.strip()}"
        combined = stamped_note if not ticket["notes"] else f"{ticket['notes']}\n{stamped_note}"
        connection.execute(
            "UPDATE tickets SET notes = ? WHERE id = ?", (combined, ticket_id)
        )
        connection.commit()
        updated = connection.execute(
            "SELECT * FROM tickets WHERE id = ?", (ticket_id,)
        ).fetchone()
    return dict(updated)


@mcp.tool()
def update_ticket_status(
    ticket_id: int,
    status: str,
    note: str,
    updated_by: str,
) -> dict[str, Any]:
    """Update a ticket status and append an auditable board note."""
    if status not in VALID_TICKET_STATUSES:
        raise ValueError(f"status must be one of {sorted(VALID_TICKET_STATUSES)}")
    if not note.strip() or not updated_by.strip():
        raise ValueError("note and updated_by are required")
    if status == "resolved" and updated_by.strip().lower() in AGENT_IDENTITIES - {"boss"}:
        raise PermissionError("Only Boss or a human may mark a ticket resolved")

    with WRITE_LOCK, closing(_connect(read_only=False)) as connection:
        ticket = connection.execute(
            "SELECT * FROM tickets WHERE id = ?", (ticket_id,)
        ).fetchone()
        if ticket is None:
            raise LookupError(f"No ticket found with id {ticket_id}")
        shop_date = connection.execute("SELECT date_today FROM desk LIMIT 1").fetchone()
        stamped_note = f"[{shop_date['date_today']}] {updated_by.strip()}: {note.strip()}"
        combined = stamped_note if not ticket["notes"] else f"{ticket['notes']}\n{stamped_note}"
        connection.execute(
            "UPDATE tickets SET status = ?, notes = ? WHERE id = ?",
            (status, combined, ticket_id),
        )
        connection.commit()
        updated = connection.execute(
            "SELECT * FROM tickets WHERE id = ?", (ticket_id,)
        ).fetchone()
    return dict(updated)


@mcp.tool()
def record_approved_payment(
    kind: str,
    ref_id: int,
    amount: float,
    account: str,
    approved_by: str,
) -> dict[str, Any]:
    """Record an approved invoice or rent payment while enforcing cash and approval rules."""
    normalized_kind = kind.strip().lower()
    if normalized_kind not in {"invoice", "rent"}:
        raise ValueError("kind must be 'invoice' or 'rent'")
    if amount <= 0:
        raise ValueError("amount must be greater than zero")
    if not approved_by.strip() or approved_by.strip().lower() in {
        "agent",
        "system",
        "automatic",
        "auto",
        *AGENT_IDENTITIES,
    }:
        raise PermissionError("A human approval name is required for every payment")

    with WRITE_LOCK, closing(_connect(read_only=False)) as connection:
        today = connection.execute("SELECT date_today FROM desk LIMIT 1").fetchone()
        cash = connection.execute(
            "SELECT * FROM cash_accounts WHERE name = ?", (account,)
        ).fetchone()
        if cash is None:
            raise LookupError(f"No cash account found named {account!r}")
        if cash["balance"] < amount:
            raise ValueError("Payment refused: insufficient cash; balance cannot go negative")

        if normalized_kind == "invoice":
            reference = connection.execute(
                "SELECT * FROM invoices WHERE id = ?", (ref_id,)
            ).fetchone()
            if reference is None:
                raise LookupError(f"No invoice found with id {ref_id}")
            if reference["status"] != "open":
                raise ValueError("Invoice is not open and cannot be paid again")
            if amount != reference["amount"]:
                raise ValueError("Invoice payment must equal the invoice amount")
            payment_kind = "invoice"
            expected_amount = reference["amount"]
            connection.execute(
                "UPDATE invoices SET status = 'paid' WHERE id = ?", (ref_id,)
            )
        else:
            reference = connection.execute(
                "SELECT * FROM leases WHERE id = ?", (ref_id,)
            ).fetchone()
            if reference is None:
                raise LookupError(f"No lease found with id {ref_id}")
            if amount != reference["monthly_rent"]:
                raise ValueError("Rent payment must equal the lease monthly rent")
            payment_kind = "rent"
            expected_amount = reference["monthly_rent"]

        connection.execute(
            """
            INSERT INTO payments(kind, ref_id, amount, account, paid_at, approved_by)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (payment_kind, ref_id, expected_amount, account, today["date_today"], approved_by.strip()),
        )
        connection.execute(
            "UPDATE cash_accounts SET balance = balance - ?, date = ? WHERE name = ?",
            (expected_amount, today["date_today"], account),
        )
        connection.commit()
        payment = connection.execute(
            "SELECT * FROM payments WHERE id = last_insert_rowid()"
        ).fetchone()
        new_cash = connection.execute(
            "SELECT * FROM cash_accounts WHERE name = ?", (account,)
        ).fetchone()

    return {"payment": dict(payment), "cash_account": dict(new_cash)}


if __name__ == "__main__":
    mcp.run()
