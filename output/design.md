# Agent Dashboard Design

## Overall direction

The dashboard is designed as a warm, restrained operations briefing room: ivory paper, espresso ink, muted brass, and sage green. The visual language is intentionally closer to a well-made consultant's desk book than a noisy command center. It gives the human a quiet place to make decisions while the agents do the busy work.

## Layout

- A compact top bar identifies Campus Customs, shows the MCP connection, and keeps the reset action available but visually quiet.
- The briefing header puts the purpose first and makes the checking balance visible without requiring a second screen.
- A left ticket rail keeps all three tickets available for quick selection. The selected ticket has a warm inset edge, while status colors remain restrained.
- The main workspace contains the selected ticket facts, a five-agent room, a live event timeline, and a human checkpoint card.
- The page polls the FastAPI backend so the ticket list, cash balance, events, and linked approval context refresh while a run is in progress.

## How agents read differently

Each agent has a compact “desk card” with initials, role, current state, latest summary, and the MCP tool it most recently opened. Active agents receive a small green pulse and a slightly brighter card, so motion is visible without becoming distracting. The event timeline then supplies the detail: delegations read as handoffs, MCP calls read as evidence gathering, and completed delegations read as specialist reports.

## Resolved tickets and cash

Ticket status comes from the backend/MCP data rather than a frontend guess. Open, in-progress, waiting-for-approval, and resolved states have distinct but quiet treatments. The cash card stays in the briefing header so a human can see the checking balance before approving anything. The approval panel only becomes actionable when the run asks for human approval; it is prefilled from the selected ticket's MCP-backed invoice or lease context. After approval, the dashboard refreshes the balance and ticket board.

## The human-friendly creative choice

The special touch is the “desk ritual” language and the briefing-room metaphor: the interface asks the human to make “the next good decision,” labels the activity area “The room,” and uses a small brass-style star note to remind them to invite only the right specialist. It gives the operator a sense of stewardship rather than making them feel like an emergency button-pusher. The agents are visually busy only when they have evidence to gather; the human remains the calm editor of the final decision.
