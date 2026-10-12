"""Small shared factory for the five role-specific agents."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from pydantic_ai import Agent

from ..models import AgentDecision, AgentRole, TeamDeps
from .common import install_common_tools


PROMPT_ROOT = Path(__file__).resolve().parents[1] / "prompts"


def build_role_agent(
    model: Any,
    role: AgentRole,
    prompt_filename: str,
    description: str,
) -> Agent[TeamDeps, AgentDecision]:
    prompt = (PROMPT_ROOT / prompt_filename).read_text(encoding="utf-8")
    agent = Agent(
        model=model,
        name=role,
        description=description,
        deps_type=TeamDeps,
        output_type=AgentDecision,
        instructions=prompt,
        model_settings={"openai_reasoning_effort": "none"},
        retries=2,
        tool_timeout=45,
    )
    install_common_tools(agent, role)
    return agent
