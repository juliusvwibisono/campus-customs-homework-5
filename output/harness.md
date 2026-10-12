# Campus Customs Database Harness Notes

## `cash_accounts`

Fields: `name`, `balance`, `date`

Why it matters: Accounting uses the account balance to verify available cash before preparing or approving payments.

## `desk`

Fields: `date_today`, `notes`

Why it matters: All agents use `date_today` as the shop's current date when deciding what is overdue or due soon.

## `inventory`

Fields: `sku`, `name`, `size`, `qty`, `location`

Why it matters: Inventory checks stock by SKU and size, identifies shortages, and provides the product location.

## `invoices`

Fields: `id`, `vendor_id`, `amount`, `due_date`, `status`, `description`

Why it matters: Accounting uses invoices to track vendor obligations and determine whether a vendor can ship more product.

## `leases`

Fields: `id`, `space_name`, `landlord`, `monthly_rent`, `next_due`, `notes`

Why it matters: Facilities uses lease details to manage the shop space and prepare rent actions.

## `payments`

Fields: `id`, `kind`, `ref_id`, `amount`, `account`, `paid_at`, `approved_by`

Why it matters: Accounting records approved payments and provides an audit trail for money leaving the shop.

## `pricing`

Fields: `sku`, `unit_cost`, `list_price`

Why it matters: Accounting and Boss use cost and list price to check margins and evaluate discount requests.

## `tickets`

Fields: `id`, `type`, `requester`, `subject`, `sku`, `size`, `qty`, `lease_id`, `invoice_id`, `status`, `notes`, `created_at`

Why it matters: Boss uses tickets as the work queue, routing each request to the appropriate agents and tracking its resolution.

## `vendors`

Fields: `id`, `name`, `specialty`, `lead_days`

Why it matters: Inventory and Accounting use vendor specialties and lead times to plan restocking and purchase orders.

## MCP tool-to-ticket map

### `list_open_tickets`

- Tables read: `tickets`
- Tickets helped: 101, 102, and 103
- Why this is the right tool: Boss needs the current open queue so it can see each ticket's type and route ticket 101 to inventory/accounting, ticket 102 to facilities/accounting, and ticket 103 to inventory/accounting.

### `list_tickets`

- Tables read: `tickets`
- Tickets helped: 101, 102, and 103
- Why this is the right tool: The dashboard needs one complete status view so it can show whether each ticket is still open or has been resolved after an agent run.

### `get_cash_balance`

- Tables read: `cash_accounts`
- Tickets helped: 101 and 102
- Why this is the right tool: Accounting and the dashboard need the current checking balance before displaying or approving the invoice or rent cash-out tied to those tickets.

### `inspect_inventory`

- Tables read: `inventory`, `pricing`
- Tickets helped: 101 and 103
- Why this is the right tool: It checks the exact SKU and size for ticket 101's size-S tee and ticket 103's 20 medium hoodies, while also providing the pricing data needed to assess the requests.

### `get_ticket_context`

- Tables read: `tickets`, `leases`, `invoices`, `vendors`, `inventory`, `pricing`, `desk`, `cash_accounts`
- Tickets helped: 101, 102, and 103
- Why this is the right tool: It gathers the records linked to each ticket, including ticket 101's unpaid vendor invoice, ticket 102's rent lease and cash/date context, and ticket 103's stock and pricing context.

### `get_restock_options`

- Tables read: `inventory`, `pricing`, `vendors`, `invoices`
- Tickets helped: 101 and 103
- Why this is the right tool: It shows the exact shortage for ticket 101's size-S tee or ticket 103's medium hoodies and identifies vendor lead times plus open-invoice shipping blocks before anyone proposes restocking.

### `append_ticket_note`

- Tables read/written: reads `desk` and `tickets`; writes `tickets`
- Tickets helped: 101, 102, and 103
- Why this is the right tool: Customer Service can place a verified draft on the relevant ticket board without emailing the customer, landlord, or vendor.

### `update_ticket_status`

- Tables read/written: reads `desk` and `tickets`; writes `tickets`
- Tickets helped: 101, 102, and 103
- Why this is the right tool: Boss can move a ticket to `in_progress`, `waiting_approval`, or `resolved` while preserving the reason in the board notes.

### `record_approved_payment`

- Tables read/written: reads `desk`, `cash_accounts`, `invoices` or `leases`; writes `payments`, `cash_accounts`, and `invoices` for invoice payments
- Tickets helped: 101 and 102
- Why this is the right tool: It can pay ticket 101's vendor invoice or ticket 102's rent only for the recorded amount, with named human approval and enough cash.

## Agent-to-tool map

| Agent | MCP tools used | Tables reached through those tools |
| --- | --- | --- |
| Boss | `list_open_tickets`, `list_tickets`, `get_ticket_context`, all delegation tools, `update_ticket_status` | `tickets`, `leases`, `invoices`, `vendors`, `inventory`, `pricing`, `desk`, `cash_accounts`, `payments` |
| Inventory | `inspect_inventory`, `get_restock_options`, `get_ticket_context` | `inventory`, `pricing`, `vendors`, `invoices`, `tickets`, `leases`, `desk`, `cash_accounts`, `payments` |
| Accounting | `get_ticket_context`, `get_restock_options`, `get_cash_balance`, `update_ticket_status` | `tickets`, `invoices`, `leases`, `vendors`, `inventory`, `pricing`, `desk`, `cash_accounts`, `payments` |
| Facilities | `get_ticket_context`, `append_ticket_note`, `update_ticket_status` | `tickets`, `leases`, `desk`, `cash_accounts`, `payments` |
| Customer Service | `get_ticket_context`, `append_ticket_note`, `list_open_tickets` | `tickets`, `leases`, `invoices`, `vendors`, `inventory`, `pricing`, `desk`, `cash_accounts`, `payments` |

All five agents also have delegation routes to all five roles, so any agent can ask any other agent for focused help. Shop data still enters the team only through MCP.

## Safety and token limits

- Require human review before any payment, discount commitment, customer message, vendor contact, or ticket resolution; drafts stay on the board.
- Require exact SKU, size, invoice/lease amount, named approver, and sufficient cash; never allow negative balances or duplicate payments.
- Keep customer information minimal, never expose API keys, and do not invent vendor terms, fees, revenue, or delivery promises.
- Each agent call is limited to eight model requests, twelve tool calls, and 900 output tokens; the team is limited to 24 steps and three delegation levels to prevent runaway loops.

## Backend routes

- `GET /` — reports that the Campus Customs API is available.
- `GET /api/tickets` — returns all three tickets and their current status through MCP.
- `GET /api/tickets/{ticket_id}/context` — returns the selected ticket's linked MCP records for the board and approval form.
- `POST /api/tickets/{ticket_id}/run` — runs the Boss-led agent team for one ticket.
- `GET /api/events?limit=100` — returns recent audit events, including agent summaries and MCP tool calls.
- `POST /api/approvals/payment` — applies a human-approved invoice or rent payment through MCP.
- `POST /api/approvals/purchase` — applies a human-approved payment for a recorded purchase invoice through MCP.
- `GET /api/cash?account=checking` — returns the current cash-account balance through MCP.
- `POST /api/reset` — restores `data/campus_customs_new.db` from the untouched original database.

Payment-write boundary: agents can prepare approval requests, but only the two FastAPI approval routes invoke `record_approved_payment` and change cash.

## React dashboard

The Vite + React + TypeScript dashboard is in `frontend/` and uses `http://localhost:8000` as its backend base URL. It lists all three tickets, lets a human select a ticket and start its Boss-led run, polls recent audit events, shows each agent's latest activity and tool, displays resolved status and the run summary, presents the human approval form for a prepared invoice or rent payment, and refreshes the checking balance after approval. Its beige, brown, and green visual language distinguishes active work, approval checkpoints, and resolved work without hiding the human decision boundary. Start it from `frontend/` with `npm run dev`.

## Problem 9 run evidence

The working copy was reset from `data/campus_customs.db` before the full run. The original starting checking balance was `$3,400.00`; the final working-copy balance is `$160.00`. Tickets 101, 102, and 103 are all `resolved` in `data/campus_customs_new.db`. The audit trail was appended throughout the runs and contains 227 records, including the three final human-resolution records. Detailed per-ticket contributions and approvals are in `output/resolved_tickets.json`; the board captures are in `output/resolved_board.html`.

Cash reconciliation: ticket 101 paid invoice 501 for `$840.00`; ticket 102 paid lease 1 rent for `$2,400.00`; ticket 103 had no cash change. Therefore `$3,400.00 - $840.00 - $2,400.00 = $160.00`, matching `cash_accounts.balance`. Both payment rows name `Human operator` in `payments.approved_by`, and invoice 501 is marked `paid`.
