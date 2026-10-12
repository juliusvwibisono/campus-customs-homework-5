import { useCallback, useEffect, useMemo, useState } from 'react'

const API_BASE = 'http://localhost:8000'
const AGENTS = ['Boss', 'Inventory', 'Accounting', 'Facilities', 'Customer Service'] as const
type AgentName = (typeof AGENTS)[number]
type TicketStatus = 'open' | 'in_progress' | 'waiting_approval' | 'resolved'

type Ticket = {
  id: number
  type: string
  requester: string
  subject: string
  sku: string | null
  size: string | null
  qty: number | null
  lease_id: number | null
  invoice_id: number | null
  status: TicketStatus
  notes: string | null
  created_at: string
}

type AuditEvent = {
  timestamp: string
  run_id?: string
  event: string
  agent?: AgentName
  delegated_to?: AgentName
  ticket_id?: number
  tool_name?: string
  summary?: string
  output_preview?: string
  task?: string
  detail?: string
  status?: TicketStatus
  needs_human_approval?: boolean
  [key: string]: unknown
}

type TicketContext = {
  ticket: Ticket
  invoice: { id: number; amount: number; status: string; description: string | null } | null
  lease: { id: number; monthly_rent: number; next_due: string; landlord: string } | null
  shop: { desk: { date_today: string }; cash_accounts: { name: string; balance: number }[] }
}

type CashAccount = { name: string; balance: number; date: string }
type RunResult = {
  summary: string
  status: TicketStatus
  needs_human_approval: boolean
  evidence: { source: string; detail: string }[]
}

type ApprovalDraft = {
  kind: 'invoice' | 'rent'
  reference_id: number
  amount: number
}

async function api<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: { 'Content-Type': 'application/json', ...(options?.headers ?? {}) },
    ...options,
  })
  if (!response.ok) {
    const detail = await response.text()
    throw new Error(detail || `Request failed (${response.status})`)
  }
  return response.json() as Promise<T>
}

function formatMoney(value: number) {
  return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(value)
}

function formatTime(value: string) {
  return new Intl.DateTimeFormat('en-US', { hour: 'numeric', minute: '2-digit' }).format(new Date(value))
}

function statusLabel(status: TicketStatus) {
  return status.replace('_', ' ')
}

function initials(name: string) {
  return name.split(' ').map((part) => part[0]).join('').slice(0, 2)
}

function eventDescription(event: AuditEvent) {
  if (event.event === 'mcp_tool_started') return `opened ${event.tool_name ?? 'an MCP tool'}`
  if (event.event === 'mcp_tool_completed') return `received data from ${event.tool_name ?? 'MCP'}`
  if (event.event === 'delegation_started') return `asked ${event.delegated_to ?? 'a specialist'} for help`
  if (event.event === 'delegation_completed') return event.summary ?? `reported back to ${event.agent ?? 'the desk'}`
  if (event.event === 'delegation_blocked' || event.event === 'limit_blocked') return event.detail ?? 'stopped at a safety limit'
  if (event.event === 'team_run_started') return 'opened the ticket briefing'
  if (event.event === 'team_run_completed') return event.summary ?? 'completed the run'
  return event.detail ?? event.event.replace(/_/g, ' ')
}

function agentSnapshot(agent: AgentName, events: AuditEvent[], running: boolean) {
  const relevant = events.filter((event) => event.agent === agent || event.delegated_to === agent)
  const latest = relevant[0]
  const completed = relevant.find((event) => event.event === 'delegation_completed' && event.delegated_to === agent)
  const tool = relevant.find((event) => event.event === 'mcp_tool_started' && event.agent === agent)
  return {
    agent,
    active: running && Boolean(latest),
    summary: completed?.summary ?? (latest ? eventDescription(latest) : 'Standing by for a focused handoff.'),
    tool: tool?.tool_name,
    latest,
  }
}

function App() {
  const [tickets, setTickets] = useState<Ticket[]>([])
  const [selectedId, setSelectedId] = useState(101)
  const [events, setEvents] = useState<AuditEvent[]>([])
  const [cash, setCash] = useState<CashAccount | null>(null)
  const [context, setContext] = useState<TicketContext | null>(null)
  const [runResult, setRunResult] = useState<RunResult | null>(null)
  const [isRunning, setIsRunning] = useState(false)
  const [isApproving, setIsApproving] = useState(false)
  const [approvedBy, setApprovedBy] = useState('')
  const [approval, setApproval] = useState<ApprovalDraft | null>(null)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')

  const selectedTicket = tickets.find((ticket) => ticket.id === selectedId) ?? null
  const ticketEvents = useMemo(
    () => events.filter((event) => event.ticket_id === selectedId),
    [events, selectedId],
  )
  const snapshots = useMemo(
    () => AGENTS.map((agent) => agentSnapshot(agent, ticketEvents, isRunning)),
    [ticketEvents, isRunning],
  )
  const needsApproval = Boolean(runResult?.needs_human_approval || selectedTicket?.status === 'waiting_approval')

  const loadTickets = useCallback(async () => {
    const data = await api<Ticket[]>('/api/tickets')
    setTickets(data)
  }, [])

  const loadContext = useCallback(async (ticketId: number) => {
    const data = await api<TicketContext>(`/api/tickets/${ticketId}/context`)
    setContext(data)
    if (data.invoice) setApproval({ kind: 'invoice', reference_id: data.invoice.id, amount: data.invoice.amount })
    else if (data.lease) setApproval({ kind: 'rent', reference_id: data.lease.id, amount: data.lease.monthly_rent })
    else setApproval(null)
  }, [])

  const refresh = useCallback(async (ticketId = selectedId) => {
    const [nextEvents, nextCash] = await Promise.all([
      api<AuditEvent[]>('/api/events?limit=250'),
      api<CashAccount>('/api/cash'),
    ])
    setEvents(nextEvents)
    setCash(nextCash)
    await loadTickets()
    await loadContext(ticketId)
  }, [loadContext, loadTickets, selectedId])

  useEffect(() => {
    refresh().catch((reason: unknown) => setError(reason instanceof Error ? reason.message : 'Could not reach the backend.'))
  }, [refresh])

  useEffect(() => {
    const interval = window.setInterval(() => {
      refresh().catch(() => undefined)
    }, 2200)
    return () => window.clearInterval(interval)
  }, [refresh])

  useEffect(() => {
    setRunResult(null)
    setNotice('')
    loadContext(selectedId).catch((reason: unknown) => setError(reason instanceof Error ? reason.message : 'Could not load ticket context.'))
  }, [loadContext, selectedId])

  async function startRun() {
    if (!selectedTicket || isRunning) return
    setError('')
    setNotice('')
    setRunResult(null)
    setIsRunning(true)
    try {
      const response = await api<{ result: RunResult }>(`/api/tickets/${selectedTicket.id}/run`, {
        method: 'POST',
        body: JSON.stringify({ instruction: `Resolve ticket ${selectedTicket.id} using only the evidence in MCP. Delegate only to the specialists this ticket needs.` }),
      })
      setRunResult(response.result)
      setNotice(response.result.status === 'resolved' ? 'Ticket resolved and written back to the board.' : 'Run complete — review the next safe action below.')
      await refresh(selectedTicket.id)
    } catch (reason: unknown) {
      setError(reason instanceof Error ? reason.message : 'The agent run failed.')
    } finally {
      setIsRunning(false)
    }
  }

  async function approvePayment() {
    if (!approval || !approvedBy.trim()) {
      setError('Enter the human approver name before approving.')
      return
    }
    setIsApproving(true)
    setError('')
    try {
      await api('/api/approvals/payment', {
        method: 'POST',
        body: JSON.stringify({ ...approval, approved_by: approvedBy.trim() }),
      })
      setNotice('Approved payment recorded. The checking balance has been refreshed.')
      await refresh(selectedId)
    } catch (reason: unknown) {
      setError(reason instanceof Error ? reason.message : 'Approval failed.')
    } finally {
      setIsApproving(false)
    }
  }

  async function resetDesk() {
    if (!window.confirm('Reset the working database to the original ticket values?')) return
    try {
      await api('/api/reset', { method: 'POST' })
      setRunResult(null)
      setNotice('Working database restored to its original values.')
      await refresh(selectedId)
    } catch (reason: unknown) {
      setError(reason instanceof Error ? reason.message : 'Reset failed.')
    }
  }

  return (
    <div className="app-shell">
      <header className="topbar">
        <div className="brand-block">
          <div className="brand-mark">CC</div>
          <div>
            <p className="eyebrow">Campus Customs</p>
            <h1>Operations desk</h1>
          </div>
        </div>
        <div className="topbar-actions">
          <div className="live-chip"><span className="live-dot" /> MCP link live</div>
          <button className="quiet-button" onClick={resetDesk}>Reset working desk</button>
        </div>
      </header>

      <main className="workspace">
        <section className="briefing-row">
          <div>
            <p className="eyebrow">Morning briefing · Campus Customs</p>
            <h2>Make the next good decision.</h2>
            <p className="lede">A calm, human-readable view of the ticket board, specialist handoffs, and approvals.</p>
          </div>
          <div className="cash-card">
            <div className="cash-label"><span className="cash-icon">$</span> Checking balance</div>
            <strong>{cash ? formatMoney(cash.balance) : '—'}</strong>
            <span className="cash-date">{cash ? `as of ${cash.date}` : 'waiting for MCP'}</span>
          </div>
        </section>

        {error && <div className="alert error"><strong>Desk note:</strong> {error}</div>}
        {notice && <div className="alert success"><strong>Updated:</strong> {notice}</div>}

        <div className="dashboard-grid">
          <aside className="ticket-column">
            <div className="section-heading"><div><p className="eyebrow">Open board</p><h3>Tickets</h3></div><span className="count-pill">{tickets.length || 3}</span></div>
            <div className="ticket-list">
              {tickets.map((ticket) => (
                <button key={ticket.id} className={`ticket-card ${ticket.id === selectedId ? 'selected' : ''}`} onClick={() => setSelectedId(ticket.id)}>
                  <div className="ticket-card-top"><span className="ticket-number">#{ticket.id}</span><span className={`status-dot ${ticket.status}`} /></div>
                  <strong>{ticket.subject}</strong>
                  <span>{ticket.requester}</span>
                  <div className="ticket-card-bottom"><span>{ticket.type.replace('_', ' ')}</span><span className={`status-text ${ticket.status}`}>{statusLabel(ticket.status)}</span></div>
                </button>
              ))}
              {!tickets.length && <div className="empty-state">Waiting for tickets from the backend…</div>}
            </div>
            <div className="desk-note"><span className="note-pin">✦</span><p><strong>Desk ritual</strong><br />Read the ticket, then invite only the right specialist.</p></div>
          </aside>

          <section className="ticket-detail">
            {selectedTicket ? (
              <>
                <div className="detail-header">
                  <div>
                    <div className="detail-kicker"><span>Ticket #{selectedTicket.id}</span><span className="slash">/</span><span>{selectedTicket.type.replace('_', ' ')}</span></div>
                    <h3>{selectedTicket.subject}</h3>
                    <p>{selectedTicket.requester} · opened {new Date(selectedTicket.created_at).toLocaleDateString()}</p>
                  </div>
                  <div className={`large-status ${selectedTicket.status}`}><span className="status-dot" />{statusLabel(selectedTicket.status)}</div>
                </div>

                <div className="fact-strip">
                  <div><span>Request</span><strong>{selectedTicket.sku ? `${selectedTicket.qty} × ${selectedTicket.sku} / ${selectedTicket.size}` : selectedTicket.subject}</strong></div>
                  <div><span>Board note</span><strong>{selectedTicket.notes?.split('\n').slice(-1)[0] ?? 'No notes yet'}</strong></div>
                </div>

                <div className="agent-panel panel-card">
                  <div className="section-heading"><div><p className="eyebrow">The room</p><h3>Agent activity</h3></div><span className={isRunning ? 'pulse-label' : 'quiet-label'}>{isRunning ? 'Live handoffs' : 'Ready when you are'}</span></div>
                  <div className="agent-grid">
                    {snapshots.map((snapshot) => (
                      <div className={`agent-card ${snapshot.active ? 'active' : ''}`} key={snapshot.agent}>
                        <div className="agent-avatar">{initials(snapshot.agent)}</div>
                        <div className="agent-info"><strong>{snapshot.agent}</strong><span>{snapshot.active ? 'working now' : 'on call'}</span></div>
                        {snapshot.active && <span className="agent-pulse" />}
                        <p>{snapshot.summary}</p>
                        {snapshot.tool && <code>{snapshot.tool}</code>}
                      </div>
                    ))}
                  </div>
                  <button className="run-button" disabled={isRunning} onClick={startRun}><span>{isRunning ? '◌' : '→'}</span>{isRunning ? 'Team is working…' : 'Start agent team'}</button>
                </div>

                <div className="lower-grid">
                  <section className="panel-card timeline-card"><div className="section-heading"><div><p className="eyebrow">Live log</p><h3>What is happening</h3></div><span className="event-count">{ticketEvents.length} events</span></div><div className="timeline">
                    {ticketEvents.length ? ticketEvents.slice(0, 12).map((event, index) => <div className="timeline-item" key={`${event.timestamp}-${index}`}><span className="timeline-line" /><div className="timeline-dot" /><div><div className="timeline-meta"><strong>{event.agent ?? event.delegated_to ?? 'Desk'}</strong><span>{formatTime(event.timestamp)}</span></div><p>{eventDescription(event)}</p></div></div>) : <div className="empty-state">Start the team to see the desk come alive.</div>}
                  </div></section>

                  <section className="panel-card decision-card"><div className="section-heading"><div><p className="eyebrow">Decision memo</p><h3>Human checkpoint</h3></div><span className="lock-icon">⌑</span></div>
                    {needsApproval ? <>
                      <p className="approval-copy">The agents have prepared a cash action. Review the database-backed amount before approving.</p>
                      <div className="approval-form">
                        <label>Approval name<input value={approvedBy} onChange={(event) => setApprovedBy(event.target.value)} placeholder="Your name" /></label>
                        <label>Action<select value={approval?.kind ?? 'invoice'} onChange={(event) => setApproval((current) => current ? { ...current, kind: event.target.value as 'invoice' | 'rent' } : current)}><option value="invoice">Pay invoice</option><option value="rent">Pay rent</option></select></label>
                        <div className="approval-facts"><span>Reference <strong>{approval?.reference_id ?? '—'}</strong></span><span>Amount <strong>{approval ? formatMoney(approval.amount) : '—'}</strong></span></div>
                        <button className="approve-button" disabled={isApproving || !approval} onClick={approvePayment}>{isApproving ? 'Recording…' : 'Approve & record payment'}</button>
                      </div>
                    </> : <div className="clear-checkpoint"><span className="check-mark">✓</span><div><strong>No approval requested</strong><p>The team can investigate this ticket without moving cash. Any future payment will pause here for a human.</p></div></div>}
                    {runResult && <div className="run-summary"><span className="eyebrow">Latest team summary</span><p>{runResult.summary}</p></div>}
                  </section>
                </div>
              </>
            ) : <div className="empty-state large">Select a ticket to open its briefing.</div>}
          </section>
        </div>
      </main>
      <footer>Campus Customs · human-led operations, thoughtfully automated</footer>
    </div>
  )
}

export default App
