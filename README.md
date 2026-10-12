# Campus Customs Multi-Agent Operations

Campus Customs is a database-backed MCP, FastAPI, PydanticAI, and React/Vite application for routing three shop operations tickets through a human-supervised agent team.

The repository intentionally includes both database files:

- `data/campus_customs.db` is the untouched reset copy.
- `data/campus_customs_new.db` is the working copy used by the MCP server and backend.

The working database is included in its current resolved state so a grader can inspect the evidence immediately. For a clean run, copy the original over the working copy before starting the three-ticket run.

## Setup

From the repository root, create a Python environment and install the combined requirements:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Edit `.env` and set `PORTKEY_API_KEY`. The agent team uses Portkey and `gpt-6-luna` only. The real `.env` is ignored by Git and must never be committed.

Install the frontend dependencies:

```powershell
Set-Location frontend
npm install
```

## Run the application

Start the MCP server from the repository root. It uses stdio and reads/writes only the working database:

```powershell
python mcp_server/server.py
```

In a second terminal, start the FastAPI backend from `backend/`:

```powershell
Set-Location backend
uvicorn main:app --reload --port 8000
```

In a third terminal, start the React dashboard from `frontend/`:

```powershell
Set-Location frontend
npm run dev
```

Open the Vite URL, normally `http://localhost:5173`. The dashboard calls the backend at `http://localhost:8000`.

## Reset before a full run

Always reset the working copy before replaying all three tickets. This leaves the original database untouched:

```powershell
Copy-Item -Force data\campus_customs.db data\campus_customs_new.db
```

Alternatively, with the backend running:

```powershell
Invoke-RestMethod -Method Post http://localhost:8000/api/reset
```

After the reset, verify that tickets 101, 102, and 103 are open and note the starting checking balance. Run each ticket from the dashboard. Agents may prepare decisions and drafts, but a human must approve every payment through the approval control. The payment route refuses insufficient cash, duplicate invoice payments, wrong amounts, and unnamed or agent approvals.

Do not email customers or contact real vendors. Customer and vendor messages remain drafts on the board. The audit trail is append-only in `output/audit_trail.json`.

## Submission evidence

- `output/desk_tickets.html` contains the Expected and Actual ticket plans, Cash reconciliation, and Reflection.
- `output/resolved_tickets.json` records final statuses, agent contributions, and human approvals.
- `output/resolved_board.html` contains the resolved React board captures.
- `output/harness.md` documents the schema, MCP tools, agents, API routes, dashboard, and safety rules.
- `output/mcp_smoke.json` records MCP smoke-test evidence.
