# AI Prompts

## Problem 1: Vibe Coder Prompts

### Prompt I typed

> Ok now for problem 1: which is titled Vibe Coder Prompts. We have to create AI_prompts.md at the start of this assignment and we will need to keep it updated as we work. Then, we have to put one section for each problem and each section must include:
> - The problem number and title
> - At least 1 prompt I typed
> - One follow up prompt if we needed it (and one sentence on what was lacking after the first)

### Follow-up prompt

Not needed yet. The initial prompt provided all the requirements needed to create this section.

## Problem 2: Study the Campus Customs Databse

### Prompt I typed

> Yo, we need to open data/campus_customs.db and look through every table and its fields. Copy the original file to data/campus_customs_new.db - later problems update that working copy. We need to study the three open tickets so we see how they link to other tables.

### Follow-up prompt

> The first read-only database query ran into a PowerShell quoting error. Use a temporary read-only SQLite inspection script to list every table, field, foreign-key relationship, and the three open tickets with their linked records.

The first attempt lacked reliable shell quoting for the database inspection, so a temporary read-only script was needed to complete the review.

### Study notes

- The database contains `cash_accounts`, `desk`, `inventory`, `invoices`, `leases`, `payments`, `pricing`, `tickets`, and `vendors`.
- The shop date is `2026-08-31`, and checking has `$3,400.00`.
- Ticket 101 is a customer order for one `CC-TEE-WHITE` in size S. It links to invoice 501, an open $840 invoice for Bulldog Print Co. Inventory has zero size-S tees.
- Ticket 102 is a rent notice. It links to lease 1 for the Chapel Street shop, with $2,400 rent due on `2026-09-02`.
- Ticket 103 is a bulk-discount request for 20 `CC-HOOD-NAVY` hoodies in size M. Inventory has 8, so 12 are short.
- `tickets.lease_id` links to `leases.id`, and `tickets.invoice_id` links to `invoices.id`. `invoices.vendor_id` links to `vendors.id`.

### Additional follow-up prompt

> For the same problem, start output/harness.md and, for each table, list the fields and one short line explaining why that table matters for the agents.

## Problem 3: Build the MCP server

### Prompt I typed

> We have to write an MCP server in mcp_server/ using FastMCP. It will talk to data/campus_customs_new.db. We do not need to connect or run it in this problem. Also, we need to write 3 tools we know we will need for the tickets in the database. Keep the names clear. Never invent any data, only use information in the database.

### Follow-up prompt

> The server passes a syntax check, but the current environment only has fastmcp-slim without server support. Add a requirements declaration for the FastMCP server extra, but do not install dependencies or start the server because this problem does not require running it.

The first implementation prompt did not account for the local environment's missing FastMCP server extra.

### Additional follow-up prompt

> In output/harness.md, list each of the three MCP tools. For every tool include which table it reads, which ticket it helps unlock (101, 102, or 103), and one sentence explaining why that tool is right for that ticket. Also add a short mcp_server/README.md explaining the server's purpose, database file, and three tools.

## Problem 4: Add the MCP server to vibe coder and test each tool

### Prompt I typed

> In our vibe coder, add our MCP server to this project so the vibe coder can call the tools. Save the connection JSON text in .mcp.json at the project root (or however our vibe coder saves local MCP server lists). With our vibe coder connected, test each of our three MCP tools. Save the evidence in output/mcp_smoke.json. For every tool include the prompt we asked the vibe coder, the tool name, and the tool output, which must match values in data/campus_customs_new.db.

### Follow-up prompt

> The current environment's fastmcp-slim package is missing the optional server support. Install the declared server extra, connect through the project MCP configuration, test all three tools, and save their exact outputs in output/mcp_smoke.json.

The initial prompt did not account for the missing local FastMCP server dependency or specify how to capture structured tool results as evidence.

## Problem 5: Build the agent team and grow the MCP tools

### Prompt I typed

> Build the agentic team for Campus Customs using PydanticAI: Boss, Inventory, Accounting, Facilities and Customer Service. Include prompts, models, and agent loops so they can delegate work to each other with full connectivity. Put the agent prompts in backend/prompts/ - one file per agent. Put data types in backend/models.py, and the agent files under backend/ (our layout can vary as long as the 5 roles are clear). Use our PORTKEY_API_KEY and only gpt-6-luna for every agent.
>
> Let's make the prompts detailed and should cover all aspects of an agent's work
>
> THEN - we add any tools the agents need to our MCP server so they can work on the open tickets. Shop facts come from the MCP server over data/campus_customs_new.db - do not invent a second shop-tools layer that bypasses MCP. Wire the agents so they append to output/audit_trail.json as they run: for each agent-loop step, record enough to audit later. Append to this file - do not wipe it each run.
>
> In output/harness.md, list each agent and each MCP tool (including ones we add in this problem) along with which table the tool uses. Also add a short safety section: the guardrails a real business would want when agents touch real customers and real money, plus limits that keep token use in check.
>
> Update mcp_server/README.md so the tool list matches what you have now.

### Follow-up prompt

Not needed yet. The team, expanded MCP tools, prompts, audit trail, harness map, and README have been added; static validation is next.

## Problem 6: Plan the three tickets

### Prompt I typed

> Before we write the backend, write down what we expect the team to do on each open ticket. Build output/desk_tickets.html as a page I can double-click, with one tab per ticket (101, 102, and 103). Also add empty Cash and Reflection tabs for later problems. On each ticket tab, fill an Expected section only and leave room for an Actual section after the agents run.
>
> For each ticket's Expected section, explain in our words who Boss should call first and why, all expected agent delegations without sending every specialist to every ticket, and which MCP tools the run should use.

### Follow-up prompt

Not needed yet. The expected plans and placeholder Actual, Cash, and Reflection tabs are included in the HTML page.

## Problem 7: Backend routes

### Prompt I typed

> In backend/main.py, use FastAPI and add routes for the React dashboard: return the three tickets and whether each is open or resolved; take a ticket id and run the agent team; return recent agent events showing what each agent said and which tools they used; approve a payment or purchase after a human clicks approve, with the route making the cash change; return the current checking balance; and reset the working database to the original values. Startable from backend/ with `uvicorn main:app --reload --port 8000`. List each route in output/harness.md with its URL and purpose.

### Follow-up prompt

Not needed yet. The FastAPI routes and route documentation are now in place; they have not been started or used to mutate the working database.

## Problem 8: Agent Dashboard

### Prompt I typed

> Build the frontend dashboard in frontend/ with React, Vite, and TypeScript. It should call the backend at http://localhost:8000, list all three tickets, let a user pick a ticket and start the agent team, show each agent's activity and summaries while it runs, reflect resolved status, allow human approval of a requested payment or purchase, and show checking balance changes. Use a thoughtful neutral beige/brown McKinsey-style desk aesthetic. Add output/design.md explaining the layout, agent presentation, resolved/cash states, and the creative human-friendly touch. Startable with npm run dev.

### Follow-up prompt

> The strict Vite TypeScript build reports that the side-effect CSS import has no declaration. Add the standard Vite CSS/module declaration, rebuild the dashboard, and keep the design documentation accurate.

The first dashboard prompt did not account for strict TypeScript needing a declaration for the imported stylesheet.

## Problem 9: Resolve the tickets

### Prompt I typed

> Before testing the agents on a full run over the three tickets, reset the working database `data/campus_customs_new.db` again so we start clean. Note the starting checking balance. Then run all three tickets on the board (101, 102, 103) until each is resolved. Open `output/desk_tickets.html` and fill each Actual section with which agents worked, what they delegated, and which tools they used, while keeping Expected. Fill the Cash tab with the starting balance, each ticket's cash change and reason, and the ending balance. Also save `output/resolved_tickets.json` with each ticket's final status, outcome, agent contributions, and human approvals, save `output/resolved_board.html` with a board capture for each resolved ticket, append the real runs to `output/audit_trail.json`, and finish `output/harness.md` with the tables, MCP tools, agents, routes, dashboard, and safety rules.

### Follow-up prompt

> Continue the full run using only `gpt-6-luna` through Portkey. If the model rejects function tools because reasoning effort is enabled, set the model setting to `openai_reasoning_effort="none"`; keep bounded per-agent request/tool limits, preserve the append-only audit trail, and use human approval routes for all cash changes.

The first run lacked the Portkey compatibility setting for function tools and needed a bounded request-limit adjustment so the agents could finish their evidence review without runaway token use.

## Problem 10: Reflection

### Prompt I typed

> Open `output/desk_tickets.html` and fill the Reflection tab. Write in my voice as an MBA student recruiting for investment banking: stern and serious, with slightly witty phrasing. Be detailed and thorough. Evaluate the agents on tickets 101, 102, and 103; compare Actual with each Expected plan; explain what would have been simpler as one agent with tools and why; describe three new Campus Customs problems this team could solve with the tools built; and describe three new problems it could not solve, including the tools and agents needed. Tie every answer to the ticket tabs and the Cash tab as evidence from this app.

### Follow-up prompt

Not needed. The first prompt specified the required voice, all reflection questions, the evidence source, and the level of detail needed.
