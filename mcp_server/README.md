# Campus Customs MCP Server

This MCP server gives the Campus Customs agent team database-backed tools for reviewing and resolving the shop's open tickets. Agents call this server for shop facts; they do not open SQLite directly. Read tools return database values, while write tools enforce the shop's approval and cash guardrails.

It uses the working database file:

`../data/campus_customs_new.db`

The original `data/campus_customs.db` remains untouched so the working database can be reset.

## Tools

- `list_open_tickets` reads the `tickets` table and returns the current open work queue for Boss.
- `list_tickets` reads the `tickets` table and returns all tickets, including resolved tickets, for the dashboard.
- `get_cash_balance` reads `cash_accounts` and returns the current balance for a named account.
- `inspect_inventory` reads `inventory` and `pricing` for an exact SKU and size, including an optional calculated shortage for a requested quantity.
- `get_ticket_context` reads a ticket and its linked lease, invoice, vendor, inventory, pricing, shop date, cash-account, and payment records when those links exist.
- `get_restock_options` reads inventory, pricing, vendors, and open invoices to show stock shortfalls, lead times, and vendor shipping blocks.
- `append_ticket_note` appends an agent draft or review note to `tickets.notes`; it never sends a message.
- `update_ticket_status` updates a ticket status and appends an auditable note. Only Boss or a human may set `resolved`.
- `record_approved_payment` records an invoice or rent payment only with a named human approver, checks the exact recorded amount, updates the relevant invoice when applicable, and refuses negative cash balances.

The agent team can read and prepare decisions through these tools, but it does not receive the payment-write wrapper. Only the FastAPI human-approval routes call `record_approved_payment` to change cash.

The write tools operate only on `data/campus_customs_new.db`; `data/campus_customs.db` remains the reset copy.

The server is implemented with FastMCP in `server.py`.
